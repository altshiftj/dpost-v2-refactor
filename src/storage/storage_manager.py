from pathlib import Path
import shutil
import logging
from typing import Callable
from src.storage.path_manager import PathManager
from src.app.logger import setup_logger

logger = setup_logger(__name__)


class StorageManager:
    """
    The StorageManager class provides methods to move and rename files and directories
    within the application's directory structure using pathlib.
    It ensures that storage actions adhere to naming conventions and prevents filename
    conflicts by generating unique filenames when necessary.
    """

    @staticmethod
    def move_item(src: str, dest: str) -> None:
        """
        Move an item from src to dest using pathlib.
        If Path.rename() fails, fallback to shutil.move.

        Args:
            src (str): Source file or directory path.
            dest (str): Destination file or directory path.

        Raises:
            Exception: If both Path.rename() and shutil.move fail.
        """
        src_path = Path(src)
        dest_path = Path(dest)
        try:
            src_path.rename(dest_path)
        except OSError as e:
            logger.warning(
                "Path.rename() failed for '%s' to '%s': %s. Attempting shutil.move.",
                src,
                dest,
                e,
            )
            try:
                shutil.move(src, dest)
            except Exception as e_move:
                logger.error(
                    "Failed to move '%s' to '%s' using shutil.move: %s.",
                    src,
                    dest,
                    e_move,
                )
                raise e_move

    @classmethod
    def _move_to_folder(
        cls,
        src: str,
        filename_prefix: str,
        extension: str,
        unique_path_func: Callable[[str], str],
        log_message: str,
        log_level: int = logging.INFO,
    ) -> None:
        """
        Internal helper to move items to a designated folder using a unique path function.

        Args:
            src (str): Source file path.
            filename_prefix (str): Base name for the file (without extension).
            extension (str): File extension (e.g., '.txt').
            unique_path_func (Callable[[str], str]): A function that returns a unique destination path given a full filename.
            log_message (str): Log message template expecting two placeholders: the original and destination paths.
            log_level (int): Logging level (default is logging.INFO).
        """
        full_name = f"{filename_prefix}{extension}"
        dest = unique_path_func(full_name)
        cls.move_item(src, dest)
        logger.log(log_level, log_message.format(src, dest))

    @classmethod
    def move_to_exception_folder(
        cls, src: str, filename_prefix: str, extension: str = ""
    ) -> None:
        """
        Move a file to the exceptions directory with a unique name.
        """
        cls._move_to_folder(
            src=src,
            filename_prefix=filename_prefix,
            extension=extension,
            unique_path_func=PathManager.get_exception_path,
            log_message="Moved '{}' to exceptions folder at '{}'",
            log_level=logging.WARNING,
        )

    @classmethod
    def move_to_rename_folder(
        cls, src: str, filename_prefix: str, extension: str = ""
    ) -> None:
        """
        Move a file to the rename directory with a unique name.
        """
        cls._move_to_folder(
            src=src,
            filename_prefix=filename_prefix,
            extension=extension,
            unique_path_func=PathManager.get_rename_path,
            log_message="Moved '{}' to rename folder at '{}'",
            log_level=logging.INFO,
        )

    @classmethod
    def move_to_record_folder(
        cls, src: str, filename_prefix: str, extension: str = ""
    ) -> None:
        """
        Move a file to the record directory for a given record ID.
        """
        cls._move_to_folder(
            src=src,
            filename_prefix=filename_prefix,
            extension=extension,
            unique_path_func=PathManager.get_record_path,
            log_message="Moved '{}' to record folder for '{}'",
            log_level=logging.INFO,
        )
