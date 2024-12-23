"""
local_record.py

This module defines data structures for managing records associated with devices.
It includes the `RecordInfo` dataclass for storing metadata about a record and the
`LocalRecord` dataclass for tracking individual records, their associated files, and
their synchronization status with a remote database.
"""

import os
from dataclasses import dataclass, field
from typing import Dict

from src.app.logger import setup_logger

# Initialize the logger for this module
logger = setup_logger(__name__)

@dataclass
class RecordInfo:
    """
    A dataclass that holds metadata information about a record.

    Attributes:
        device_id (str): Identifier for the device generating the record.
        date (str): The date when the record was created.
        daily_record_count (int): The count of records created on the given date.
        data_type (str): The type of data the record contains (e.g., 'IMG', 'ELID').
        institute (str): The institute associated with the record.
        user_id (str): The ID of the user who created the record.
        sample_id (str): The identifier for the sample associated with the record.
    """
    device_id: str = "null"
    date: str = "null"
    daily_record_count: int = -1
    data_type: str = "null"
    institute: str = "null"
    user_id: str = "null"
    sample_id: str = "null"


@dataclass
class LocalRecord:
    """
    A dataclass that represents a local record, tracking its unique identifiers,
    name, database status, and associated files.

    Attributes:
        long_id (str): A detailed unique identifier for the record, potentially including
                      device ID, date, and other metadata.
        short_id (str): A concise unique identifier for the record.
        name (str): A user-friendly name for the record, typically derived from the sample ID.
        is_in_db (bool): Flag indicating whether the record has been uploaded to the database.
        file_uploaded (Dict[str, bool]): A dictionary mapping file paths to their upload status.
                                         The key is the file path, and the value is a boolean indicating
                                         if the file has been uploaded (`True`) or not (`False`).
    """
    long_id: str = "null"
    short_id: str = "null"
    name: str = "null"
    is_in_db: bool = False
    file_uploaded: Dict[str, bool] = field(default_factory=dict)

    def add_item(self, path: str):
        """
        Adds a file or directory to the record's `file_uploaded` dictionary.
        If the path is a file, it's added directly. If it's a directory, all files
        within that directory (and its subdirectories) are added.

        Args:
            path (str): The file or directory path to add to the record.
        """
        if os.path.isfile(path):
            # Add the single file with upload status set to False
            self.file_uploaded[path] = False
            logger.debug(f"Added file to record: {path}")
        elif os.path.isdir(path):
            # Recursively add all files in the directory
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    self.file_uploaded[file_path] = False
                    logger.debug(f"Added file to record from directory: {file_path}")
        else:
            # Log a warning if the path is neither a file nor a directory
            logger.warning(f"Path '{path}' is neither a file nor a directory.")

    def mark_uploaded(self, file_path: str):
        """
        Marks a specific file in the record as uploaded.

        Args:
            file_path (str): The path of the file to mark as uploaded.
        """
        if file_path in self.file_uploaded:
            self.file_uploaded[file_path] = True
            logger.debug(f"Marked file as uploaded: {file_path}")
        else:
            logger.warning(f"Tried to mark non-existent file as uploaded: {file_path}")

    def count_files(self) -> int:
        """
        Counts the total number of files associated with the record.

        Returns:
            int: The total number of files.
        """
        total_files = len(self.file_uploaded)
        logger.debug(f"Total files in record '{self.short_id}': {total_files}")
        return total_files

    def all_files_uploaded(self) -> bool:
        """
        Checks if all files associated with the record have been uploaded.

        Returns:
            bool: `True` if all files are uploaded, `False` otherwise.
        """
        all_uploaded = all(self.file_uploaded.values())
        logger.debug(f"All files uploaded for record '{self.short_id}': {all_uploaded}")
        return all_uploaded

    def to_dict(self) -> dict:
        """
        Serializes the LocalRecord instance into a dictionary suitable for JSON storage.

        Returns:
            dict: A dictionary representation of the LocalRecord.
        """
        record_dict = {
            "short_id": self.short_id,
            "long_id": self.long_id,
            "name": self.name,
            "is_in_db": self.is_in_db,
            "files_uploaded": self.file_uploaded,
        }
        logger.debug(f"Serialized record '{self.short_id}' to dict.")
        return record_dict

    @classmethod
    def from_dict(cls, data: dict) -> "LocalRecord":
        """
        Deserializes a dictionary into a LocalRecord instance.

        Args:
            data (dict): A dictionary containing record data, typically loaded from JSON.

        Returns:
            LocalRecord: The deserialized LocalRecord object.
        """
        record = cls(
            short_id=data.get("short_id", ""),
            long_id=data.get("long_id", ""),
            name=data.get("name", ""),
            is_in_db=data.get("is_in_db", False),
            file_uploaded=data.get("files_uploaded", {})
        )
        logger.debug(f"Deserialized record from dict: {record.short_id}")
        return record
