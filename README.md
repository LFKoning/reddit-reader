# Reddit Reader

## Goal

Exploratory project for downloading data from the Reddit API. Uses the `PRAW` package
for downloading and adds some convenience functions for processing and storing the
data.

## Usage

The `reddit_reader` package contains all the relevant code to create a `RedditReader`:

```python
from reddit_reader.reader import RedditReader

reader = RedditReader(
    storage_path="reddit_data",
    config_path="reddit_reader/default_config.yaml",
    enable_json=True,
)
```

The `storage_path` argument tells the `RedditReader` where to store the data; it creates
a SQLite database and (optionally) folders for the JSON files.

The `config_path` argument should point to a YAML file defining which fields should be
included in the output. Check `reddit_reader/default_config.yaml` for an example.

The `enable_json` parameter specifies whether the data should also be stored in JSON
format. If enabled, this creates a folder for each Subreddit within the specified
`storage_path` folder. Submissions and comments will be stored in separate subfolders.
So downloading the Subreddt `"beleggen"` would create this folder structure:

```
reddit_data/
|
+-- beleggen/
    |
    +- comments/
    +- submissions/
```

Next, you will need to connect to the Reddit API like so:

```python
reader.connect(
    username="< your Reddit user >",
    password="< your Reddit password >",
    app_id="< your Reddit app ID >",
    app_secret="< your Redd app secret >",
)
```

For the `username` and `password` arguments, fill in your Reddit username and password respectively. The `app_id` and `app_secret` arguments require you to make a Reddit app.

To create an app, go to: https://www.reddit.com/prefs/apps. Log in with your Reddit user account and select "Create app`. Supply a name for the app, select "Script for personal use" as type and fill in the requested descriptive information. Create the app and use the generated app ID and secret for the Reddit reader.

Finally, you can start downloading Reddit data using the download method:

```Python
reader.download("< subreddit name >", limit=250, more_comments=150)
```

The reader will write the results to the storage location you have specified earlier. Note that the Reddit API will limit you to 1000 results per day; so that is the maximum for the `limit` argument. The `more_comments` argument controls how many additional comments are downloaded. Reddit initially hides comments deeper in the comment tree when a thread has many comments. 

## Installation

To install this project, clone the repo:

```
git clone https://github.com/LFKoning/reddit-reader.git
```

Next install the requirements for the RedditReader:

```
pip install requirements.txt
```

Note: This will only install dependencies for the RedditReader! To run the Notebooks,
please install the additional requirements manually.
