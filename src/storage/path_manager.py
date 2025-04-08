"""
path_manager.py

This module defines the PathManager class, which handles the construction and validation
of file and directory paths within the application. It ensures that all necessary directories
exist, sanitizes user inputs to conform to naming conventions, and generates unique filenames
to prevent conflicts.
"""

from pathlib import Path

from src.config.settings import (
    WATCH_DIR,
    DEST_DIR,
    RENAME_DIR,
    EXCEPTIONS_DIR,
    FILENAME_PATTERN,
    ID_SEP,
)
from src.app.logger import setup_logger

logger = setup_logger(__name__)


class PathManager:
    """
    The PathManager class manages file and directory paths used in the application.

    Responsibilities:
        - Ensures required directories exist.
        - Sanitizes and validates user inputs to adhere to naming conventions.
        - Generates unique filenames to avoid naming conflicts.
        - Constructs paths for records, renaming operations, and exception handling.
    """

    @staticmethod
    def init_dirs(directories: list[str] = None):
        """
        Ensures all specified directories exist. Defaults to core application directories.

        Args:
            directories (list[str], optional): A list of directory paths to initialize.
                                               Defaults to WATCH_DIR, DEST_DIR, RENAME_DIR, and EXCEPTIONS_DIR.
        """
        if directories is None:
            from src.config.settings import (
                WATCH_DIR,
                DEST_DIR,
                RENAME_DIR,
                EXCEPTIONS_DIR,
            )

            directories = [WATCH_DIR, DEST_DIR, RENAME_DIR, EXCEPTIONS_DIR]

        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_record_path(filename_prefix: str) -> str:
        """
        Builds and returns the directory path for a given record, creating it if needed.
        The path is structured as: DEST_DIR / INSTITUTE.upper() / USER_ID.upper() / SAMPLE_ID.
        """
        user_ID, institute, sample_ID = filename_prefix.split(ID_SEP)
        record_path = Path(DEST_DIR) / institute.upper() / user_ID.upper() / sample_ID
        record_path.mkdir(parents=True, exist_ok=True)
        return str(record_path)

    @classmethod
    def get_rename_path(cls, name: str, base_dir: str = None) -> str:
        """
        Returns a unique path in the rename directory.

        Args:
            name (str): The filename (with extension).
            base_dir (str, optional): The base directory to use. Defaults to RENAME_DIR from settings.

        Returns:
            str: A unique full path in the rename directory.
        """
        from src.config.settings import RENAME_DIR

        base_dir = base_dir or RENAME_DIR
        filename_prefix, extension = Path(name).stem, Path(name).suffix
        return cls.get_unique_filename(base_dir, filename_prefix, extension)

    @classmethod
    def get_exception_path(cls, name: str, base_dir: str = None) -> str:
        """
        Returns a unique path in the exceptions directory.

        Args:
            name (str): The filename (with extension).
            base_dir (str, optional): The base directory to use. Defaults to EXCEPTIONS_DIR from settings.

        Returns:
            str: A unique full path in the exceptions directory.
        """
        from src.config.settings import EXCEPTIONS_DIR

        base_dir = base_dir or EXCEPTIONS_DIR
        filename_prefix, extension = Path(name).stem, Path(name).suffix
        return cls.get_unique_filename(base_dir, filename_prefix, extension)

    @staticmethod
    def get_unique_filename(
        directory: str, filename_prefix: str, extension: str
    ) -> str:
        """
        Generates a unique filename in the given directory by appending
        an incrementing counter if needed.

        e.g. if "my_file_01.txt" exists, next might be "my_file_02.txt".
        """
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)

        # Step 1: find the highest counter used by existing files with a matching extension & prefix
        counter = 1
        for existing in dir_path.iterdir():
            if existing.is_file() and existing.suffix == extension:
                existing_prefix = existing.stem
                # The logic from the original code attempts to parse
                # out a trailing counter from the file's name, after the last ID_SEP.
                prefix_no_counter = existing_prefix.rsplit(ID_SEP, 1)[0]
                if prefix_no_counter in filename_prefix:
                    # Try to parse out that trailing number
                    try:
                        suffix_num = int(existing_prefix.rsplit(ID_SEP, 1)[1])
                        if suffix_num >= counter:
                            counter = suffix_num + 1
                    except (ValueError, IndexError):
                        continue

        # Step 2: build a candidate filename that doesn't exist yet
        while True:
            candidate_name = f"{filename_prefix}{ID_SEP}{counter:02d}{extension}"
            candidate_path = dir_path / candidate_name
            if not candidate_path.exists():
                return str(candidate_path)
            counter += 1
