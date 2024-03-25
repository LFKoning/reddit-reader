"""Module for managing SQLite3 databases."""

import os
import sqlite3
from typing import Union


class Database:
    """Class for managing SQLite3 databases."""

    DDL_file = "create_tables.sql"

    def __init__(self, database_path: str) -> None:
        self._path = database_path
        self._db = None

    @property
    def database(self) -> None:
        """SQLite3 database connection."""
        if not self._db:
            self._db = sqlite3.connect(self._path)
        return self._db

    def disconnect(self) -> None:
        """Disconnect from the SQLite3 database."""
        if self._db:
            self._db.close()
            self._db = None

    def setup(self, table_sql: str, purge: bool = False) -> None:
        """Create the database, purge if requested.

        Parameters
        ----------
        table_sql : str
            SQL script with CREATE TABLE statements.
        purge : bool, default=False
            Delete the database before creating it.
        """
        if purge:
            self.disconnect()
            if os.path.isfile(self._path):
                os.remove(self._path)

        cursor = self.database.cursor()
        cursor.executescript(table_sql)
        cursor.close()

    def query(self, query: str, parameters: list = None) -> Union[list, int]:
        """Execute the SQL statement against the database.

        Parameters
        ----------
        query : str
            SQL query to perform.
        parameters : list, optional
            List of parameter values.

        Returns
        -------
        list or int
            List of dicts for SELECT queries, affected rows
            for other query types.
        """
        with self.database:
            cursor = self.database.cursor()
            if parameters:
                result = cursor.execute(query, parameters)
            else:
                result = cursor.execute(query)

            # CREATE / INSERT / UPDATE queries
            if cursor.description is None:
                result = result.rowcount

            # SELECT queries
            else:
                columns = [col[0] for col in cursor.description]
                result = [dict(zip(columns, row)) for row in result.fetchall()]

            cursor.close()

        return result

    def list_tables(self) -> list:
        """List tables in the database.

        Returns
        -------
        list
            Listing of available tables.
        """
        tables = self.query("SELECT name FROM sqlite_master WHERE type='table';")
        return [table["name"] for table in tables]

    def write(self, table: str, records: list, exists: str = "replace") -> int:
        """Write a list of dicts to a table.

        Parameters
        ----------
        table : str
            Name of the table to insert data into.
        records : list
            List of records, stored as dicts.
        exists : {"replace", "purge"}
            How to handle existing data:
            - "ignore" ignores new records when an existing record is found.
            - "replace" replaces the existing record with the new one.
            - "update" alias for "replace".
            - "append" tries to insert and errors when a record exists.
            - "purge" empties the table before inserting.

        Returns
        -------
        int
            Number of rows inserted or updated.
        """
        # Empty table if "purge" was selected.
        if exists == "purge":
            self.truncate(table)

        # Determine which operation to perform.
        command = "INSERT"
        if exists in ("replace", "update"):
            command = "INSERT OR REPLACE"
        elif exists == "ignore":
            command = "INSERT OR IGNORE"

        # Take column names from first record then extract all values.
        columns = records[0].keys()
        values = [
            [record.get(column, None) for column in columns] for record in records
        ]

        parameter_str = ", ".join(["?"] * len(columns))
        query = f"{command} INTO {table} ({','.join(columns)}) VALUES ({parameter_str})"

        with self.database:
            cursor = self.database.cursor()
            result = cursor.executemany(query, values)
            cursor.close()

        return result.rowcount

    def truncate(self, table: str) -> None:
        """Truncate provided table."""
        self.query(f"TRUNCATE TABLE {table};")
