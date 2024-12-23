"""
storage_manager.py

This module defines the IStorageManager interface and its concrete implementation,
StorageManager. It handles file and directory storage operations such as moving and
renaming items, ensuring that all storage actions adhere to the application's
naming conventions and directory structures.
"""

import os
import shutil
from abc import ABC, abstractmethod

from src.records.local_record import LocalRecord
from src.storage.path_manager import PathManager
from src.app.logger import setup_logger

logger = setup_logger(__name__)


class IStorageManager(ABC):
    """
    Interface for managing storage operations such as moving and renaming files.

    This abstract base class defines the essential methods that any storage manager
    implementation must provide. It ensures consistency and standardization across
    different storage operations within the application.
    """

    @abstractmethod
    def move_item(self, src: str, dest: str):
        """
        Move an item from the source path to the destination path.

        Args:
            src (str): Source file or directory path.
            dest (str): Destination file or directory path.
        """
        pass

    @abstractmethod
    def move_to_directory(self, path: str, directory: str, log_message: str):
        """
        Move a file to a specified directory with a log message.

        Args:
            path (str): Path of the file to move.
            directory (str): Target directory path.
            log_message (str): Message to log after moving.
        """
        pass

    @abstractmethod
    def move_to_exception_folder(self, path: str):
        """
        Move a file to the exceptions directory.

        Args:
            path (str): Path of the file to move.
        """
        pass

    @abstractmethod
    def move_to_rename_folder(self, path: str, name: str):
        """
        Move a file to the rename directory with a unique name.

        Args:
            path (str): Path of the file to move.
            name (str): Desired base name for the file.
        """
        pass


class StorageManager(IStorageManager):
    """
    Concrete implementation of IStorageManager that handles standard file storage operations.

    The StorageManager class provides methods to move and rename files and directories
    within the application's directory structure. It ensures that all storage actions
    comply with naming conventions and prevents filename conflicts by generating unique
    filenames when necessary.
    """

    def __init__(self, path_manager: PathManager):
        """
        Initialize the StorageManager with a PathManager instance.

        Args:
            path_manager (PathManager): An instance of PathManager to handle path operations.
        """
        self.path_manager = path_manager
        logger.debug("StorageManager initialized with PathManager.")

    def move_item(self, src: str, dest: str):
        """
        Move an item from src to dest using os.rename. If os.rename fails, fallback to shutil.move.

        This method attempts to rename/move a file or directory. If the rename operation
        fails (e.g., moving across different filesystems), it uses shutil.move as a fallback.

        Args:
            src (str): Source file or directory path.
            dest (str): Destination file or directory path.

        Raises:
            shutil.Error: If both os.rename and shutil.move fail.
        """
        try:
            os.rename(src, dest)
            logger.info(f"Moved '{src}' to '{dest}' using os.rename.")
        except OSError as e:
            logger.warning(f"os.rename failed for '{src}' to '{dest}': {e}. Attempting shutil.move.")
            try:
                shutil.move(src, dest)
                logger.info(f"Moved '{src}' to '{dest}' using shutil.move.")
            except Exception as e_move:
                logger.error(f"Failed to move '{src}' to '{dest}' using shutil.move: {e_move}.")
                raise e_move  # Re-raise exception after logging

    def move_to_directory(self, path: str, directory: str, log_message: str):
        """
        Moves the file at the given path to the specified directory with a log message.

        This method ensures that the destination directory has a unique filename to prevent
        overwriting existing files. It then moves the file and logs the provided message.

        Args:
            path (str): Path of the file to move.
            directory (str): Target directory path.
            log_message (str): Message to log after moving.
        """
        basename = os.path.basename(path)
        base_name, extension = os.path.splitext(basename)
        unique_dest_path = self.path_manager.get_unique_filename(directory, base_name, extension)
        self.move_item(path, unique_dest_path)
        logger.info(log_message + f" Moved to '{unique_dest_path}'.")

    def move_to_exception_folder(self, path: str):
        """
        Move a file to the exceptions directory.

        This is typically used when a file does not meet certain criteria and needs
        to be isolated for further inspection or handling.

        Args:
            path (str): Path of the file to move.
        """
        self.move_to_directory(
            path,
            self.path_manager.exceptions_dir,
            f"Moved '{path}' to exceptions folder."
        )

    def move_to_rename_folder(self, path: str, name: str):
        """
        Move a file to the rename directory with a unique name.

        This method is used when a file needs to be renamed to conform to naming conventions.
        It ensures the new name is unique within the rename directory to avoid conflicts.

        Args:
            path (str): Path of the file to move.
            name (str): Desired base name for the file.
        """
        unique_dest_path = self.path_manager.get_unique_filename(
            self.path_manager.rename_dir,
            name,
            ''  # Assuming no extension is needed; adjust if necessary
        )
        self.move_item(path, unique_dest_path)
        logger.info(f"Moved '{path}' to rename folder at '{unique_dest_path}'.")

