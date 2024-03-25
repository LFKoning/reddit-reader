"""Module for downloading data from the Reddit API."""
import os
import json
import time
import shutil
import logging

from pathlib import Path
from typing import Any, Union

import yaml
import praw

from praw.models import Submission, Comment, MoreComments

from .database import Database


class RedditReader:
    """Class for downloading data from the Reddit API.

    Connects via an app created on a Reddit user account.

    Parameters
    ----------
    storage_path : str
        Path to store all data; SQLite and JSON.
    config_path : str
        Path to the YAML configuraion file.
    enable_json : bool, default=True
        Store raw data as JSON, defaults to True.
    purge : bool, default=False.
        Purge the data storage, defaults to False.
    """

    USER_AGENT = "Linux:RedditReader:v0.0.1 (by /u/MorrarNL)"
    BATCH_SIZE = 30

    def __init__(
        self,
        storage_path: str,
        config_path: str,
        enable_json: bool = True,
        purge: bool = False,
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._connection = None
        self._enable_json = enable_json

        self._log.info("Creating RedditReader object.")
        self._log.debug("Reading config from: %s.", config_path)
        self._config = self._read_config(config_path)

        self._log.debug("Setting up storage in: %s.", storage_path)
        self._storage = self._setup_storage(storage_path, purge)
        self._database = self._setup_database()

    def connect(
        self, username: str, password: str, app_id: str, app_secret: str
    ) -> None:
        """Connect the Python Reddit API Wrapper (PRAW) client.

        Parameters
        ----------
        username : str
            Reddit username as string.
        password : str
            Reddit password as string.
        app_id : str
            Client ID of the Reddit app.
        app_secret : str
            Client secret of the Reddit app.
        """
        self._log.info("Connecting to Reddit with user %s and app %s", username, app_id)
        self._connection = praw.Reddit(
            user_agent=self.USER_AGENT,
            # App related credentials.
            client_id=app_id,
            client_secret=app_secret,
            # User related credentials.
            username=username,
            password=password,
        )

        # Check if the connection was succesful.
        if self._connection.user.me() == username:
            self._log.info("Succesfully connected to Reddit.")
        else:
            msg = f"Connection to Reddit failed for user {username} and app {app_id}."
            self._log.error(msg)
            raise RuntimeError(msg)

    def close(self) -> None:
        """Close connection to the SQLite database."""
        self._database.disconnect()

    def download(
        self, subreddit: str, limit: int = 1000, more_comments: int = 50
    ) -> None:
        """Download new submissions from a subreddit.

        Parameters
        ----------
        subreddit : str
            Name of the subreddit as string.
        limit : int, default=1000.
            Number of submissions to download, deafaults to 1000.
            Note that 1000 is also the cap set by Reddit.
        """
        if not self._connection:
            self._log.error("Cannot download, not connected to Reddit.")
            return

        self._log.info("Getting submissions from Reddit API.")
        self._log.debug("JSON storage enabled: %s", self._enable_json)
        submissions = list(self._connection.subreddit(subreddit).new(limit=limit))
        self._log.info("Got %d submissions.", len(submissions))

        data = []
        for submission in submissions:
            self._log.info("Downloading submission: %s", submission.name)
            raw = vars(submission)
            record = {"id": submission.name}

            # Get all fields enabled in the config.
            for field in self._config.get("submission_fields", []):
                if field not in raw:
                    self._log.warning(
                        "Field %s not in submission %s data.", field, submission.name
                    )
                    record[field] = None
                else:
                    # Convert to string.
                    record[field] = str(raw[field])

            # Store comments associated with the submission.
            self._store_comments(subreddit, submission, more_comments)

            # Store submissions in batches of 20.
            data.append(record)
            if len(data) == self.BATCH_SIZE:
                self._log.debug("Writing batch of 20 submissions.")
                self._database.write("submissions", data, exists="replace")
                data = []

            # Store submision as JSON if enabled.
            if self._enable_json:
                self._store_json("submissions", subreddit, submission)

            # Sleep to prevent HTTP 429.
            time.sleep(1)

        # Store remaining submisions.
        if data:
            self._log.debug("Writing final batch of %d submissions.", len(data))
            self._database.write("submissions", data, exists="replace")

        # Store submissions, overwriting existing records.
        self._log.info("Finished downloading from Reddit.")

    def _read_config(self, config_path: str) -> dict:
        """Read YAML config file.

        Parameters
        ----------
        config_path : str
            Path to the YAML configuration file.

        Returns
        -------
        dict
            Configuration as dict.
        """
        with open(config_path, "r", encoding="utf8") as config_file:
            config = yaml.safe_load(config_file)
        return config

    def _setup_storage(self, storage_path: str, purge: bool) -> Path:
        """Create the data storage.

        Parameters
        ----------
        storage_path : str
            Path to store all data; SQLite and JSON.
        purge : bool
            Remove all data from storage if it already exists.

        Returns
        -------
        pathlib.Path
            Path to the storage folder.
        """
        if purge and os.path.exists(storage_path):
            shutil.rmtree(storage_path)

        storage_path = Path(storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        return storage_path

    def _setup_database(self) -> None:
        """Set up the SQLite3 database."""
        self._log.info("Creating SQLite3 database in: %s", self._storage / "reddit.db")
        database = Database(self._storage / "reddit.db")

        # Create submissions table.
        self._log.debug("Creating table for submissions.")
        fields = ["id VARCHAR(20) PRIMARY KEY"]
        for field_name in self._config.get("submission_fields", []):
            fields.append(f"{field_name} TEXT NULL")
        create_sql = f"CREATE TABLE IF NOT EXISTS submissions ({', '.join(fields)});"
        database.query(create_sql)

        # Create comments table.
        self._log.debug("Creating table for comments.")
        fields = [
            "id VARCHAR(20) PRIMARY KEY",
            "parent_id VARCHAR(20) NOT NULL",
            "submission_id VARCHAR(20) NOT NULL",
        ]
        for field_name in self._config.get("comment_fields", []):
            fields.append(f"{field_name} TEXT NULL")
        create_sql = f"CREATE TABLE IF NOT EXISTS comments ({', '.join(fields)});"
        database.query(create_sql)

        return database

    def _flatten_comments(self, comments, more_comments):
        """Recursively get comments from the comment tree."""
        # Expand MoreComments if any are present.
        num_hidden = sum([isinstance(comment, MoreComments) for comment in comments])
        if num_hidden:
            self._log.info("Found %d hidden comments, downloading.", num_hidden)
            comments.replace_more(limit=more_comments)

        # Loop through comments, getting replies recursively.
        data = []
        for comment in comments:
            data.append(comment)

            if len(comment.replies) > 0:
                data.extend(self._flatten_comments(comment.replies, more_comments))

        return data

    def _store_comments(
        self, subreddit: str, submission: Submission, more_comments: int
    ) -> None:
        """Clean and store comment data.

        Parameters
        ----------
        subreddit : str
            Name of the subreddit as string.
        submission : praw.models.Submission
            PRAW Submission object to get comments from.
        """
        # No comments found, moving on.
        if not submission.comments:
            return

        self._log.info("Downloading comments for submission: %s", submission.name)
        comments = self._flatten_comments(submission.comments, more_comments)
        self._log.info("Found %d comments.", len(comments))

        data = []
        for comment in comments:
            raw = vars(comment)
            record = {
                "id": comment.name,
                "parent_id": comment.parent_id,
                "submission_id": comment.link_id,
            }

            # Get all fields enabled in the config.
            for field in self._config.get("comment_fields", []):
                if field not in raw:
                    self._log.warning(
                        "Field %s not in comment %s data.", field, comment.name
                    )
                    record[field] = None
                else:
                    # Convert to string.
                    record[field] = str(raw[field])

            # Store comments in batches.
            data.append(record)
            if len(data) == self.BATCH_SIZE:
                self._log.debug("Writing batch of 20 comments.")
                self._database.write("comments", data, exists="replace")
                data = []

            if self._enable_json:
                self._store_json("comments", subreddit, comment)

        # Store remaining comments.
        if data:
            self._log.debug("Writing final batch of %d comments.", len(data))
            self._database.write("comments", data, exists="replace")

    def _store_json(
        self,
        object_type: str,
        subreddit: str,
        reddit_object: Union[Submission, Comment],
    ) -> None:
        """Store Reddit object as JSON.

        Parameters
        ----------
        object_type : {"submissions", "comments"}
            Type of object to store.
        subreddit : str
            Name of the subreddit as string.
        reddit_object : praw.models.Submission or praw.models.Comment
            PRAW model object to store as JSON.
        """
        json_data = self._convert_dict(reddit_object)

        # Construct folder and file path.
        subreddit_path = self._storage / subreddit / object_type
        subreddit_path.mkdir(exist_ok=True, parents=True)
        json_path = subreddit_path / f"{reddit_object.name}.json"

        # Write / overwrite the file.
        with open(json_path, "w", encoding="utf8") as json_file:
            json_file.write(json.dumps(json_data, indent=2))

    def _convert_dict(self, thing: Any) -> dict:
        """Convert an object to a serializable dict.

        Parameters
        ----------
        thing : any
            Any value (int, float, str, bool) or object.

        Returns
        -------
        dict
            Object as dict, converted using vars().
        """
        # Thing is a basic types.
        base_types = (int, float, str, bool)
        if thing is None or isinstance(thing, base_types):
            return thing

        # Thing is a list or set, can contain unserializable values.
        if isinstance(thing, (list, set)):
            return [self._convert_dict(value) for value in thing]

        if isinstance(thing, dict):
            return {k: self._convert_dict(v) for k, v in thing.items()}

        # Thing is a normal object.
        if hasattr(thing, "__dict__"):
            return {
                # Convert all values in the object.
                k: self._convert_dict(v)
                for k, v in vars(thing).items()
                # Skip private attributes.
                if not k.startswith("_")
            }

        # Thing has nu __dict__ attribute, resort to dir().
        self._log.warning("Found unserializable object: %s", thing)
        return {
            attrib: getattr(thing, attrib)
            for attrib in dir(thing)
            if (
                # Skip private attrributes.
                not attrib.startswith("_")
                # Only include serializable values.
                and isinstance(getattr(thing, attrib), base_types)
            )
        }
