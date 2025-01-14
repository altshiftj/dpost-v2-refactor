"""
storage_manager.py

This module defines the IStorageManager interface and its concrete implementation,
StorageManager. It handles file and directory storage operations such as moving and
renaming items, ensuring that all storage actions adhere to the application's
naming conventions and directory structures.
"""

import os
import shutil
import logging

from src.storage.path_manager import PathManager
from src.app.logger import setup_logger

logger = setup_logger(__name__)

class StorageManager:
    """
    Concrete implementation of previous IStorageManager that handles standard file storage operations.

    Since there is no current need for multiple storage manager implementations //ALK 14.01.25

    The StorageManager class provides methods to move and rename files and directories
    within the application's directory structure. It ensures that all storage actions
    comply with naming conventions and prevents filename conflicts by generating unique
    filenames when necessary.
    """


    def move_item(self, src: str, dest: str):
        """
        Move an item from src to dest. If `os.rename` fails, fallback to `shutil.move`.

        Args:
            src (str): Source file or directory path.
            dest (str): Destination file or directory path.

        Raises:
            shutil.Error: If both os.rename and shutil.move fail.
        """
        try:
            os.rename(src, dest)
        except OSError as e:
            logger.warning(f"os.rename failed for '{src}' to '{dest}': {e}. Attempting shutil.move.")
            try:
                shutil.move(src, dest)
            except Exception as e_move:
                logger.error(f"Failed to move '{src}' to '{dest}' using shutil.move: {e_move}.")
                raise e_move  # Re-raise after logging

    @classmethod
    def _move_to_folder(
        cls,
        path: str,
        name: str,
        extension: str,
        unique_path_func,
        log_message: str,
        log_level: int = logging.INFO
    ):
        """
        Internal helper method to reduce redundancy when moving items to specific folders.

        Args:
            path (str): Path of the file to move.
            name (str): Desired base name for the file (without extension).
            extension (str): File extension (e.g., '.txt').
            unique_path_func (Callable[[str], str]): A function (e.g., `get_exception_path`)
                that returns a unique destination path given a full filename.
            log_message (str): The log message format string, expecting two placeholders:
                1) Original path
                2) Destination path
            log_level (int): The logging level to be used. Defaults to `logging.INFO`.
        """
        full_name = f"{name}{extension}"  # Combine base name and extension
        unique_dest_path = unique_path_func(full_name)
        cls.move_item(path, unique_dest_path)

        # Use the provided log level and message
        logger.log(log_level, log_message.format(path, unique_dest_path))

    @classmethod
    def move_to_exception_folder(cls, path: str, name: str, extension: str):
        """
        Move a file to the exceptions directory with a unique name.
        """
        cls._move_to_folder(
            path=path,
            name=name,
            extension=extension,
            unique_path_func=PathManager.get_exception_path,
            log_message="Moved '{}' to exceptions folder at '{}'",
            log_level=logging.WARNING
        )

    @classmethod
    def move_to_rename_folder(cls, path: str, name: str, extension: str):
        """
        Move a file to the rename directory with a unique name.
        """
        cls._move_to_folder(
            path=path,
            name=name,
            extension=extension,
            unique_path_func=PathManager.get_rename_path,
            log_message="Moved '{}' to rename folder at '{}'",
            log_level=logging.INFO
        )