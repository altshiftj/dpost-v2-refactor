from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict

from src.app.logger import setup_logger

# Initialize the logger for this module
logger = setup_logger(__name__)

@dataclass
class LocalRecord:
    """
    A dataclass that represents a local record, tracking its unique identifiers,
    name, database status, and associated files.

    Attributes:
        identifier (str): A concise unique identifier for the record for daily record storage.
        name (str): The name of the record, or record title in kadi4mat, typically derived from the sample ID.
        date (str): The date when the record was created (yyyymmdd format).
        is_in_db (bool): Flag indicating whether the record has been uploaded to the database.
        files_uploaded (Dict[str, bool]): A dictionary mapping file paths to their upload status.
                                          The key is the file path (as string), value is bool.
    """
    identifier: str = "null"
    name: str = "null"
    datatype: str = "null"
    date: str = "null"
    is_in_db: bool = False
    files_uploaded: Dict[str, bool] = field(default_factory=dict)

    def _normalized_path(self, path: str | Path) -> str:
        """
        Converts the input path to a fully resolved absolute path string.
        """
        return str(Path(path).resolve())

    def add_item(self, path: str | Path) -> "LocalRecord":
        """
        Adds a file or directory to the record's `files_uploaded` dictionary.
        If the path is a file, it's added directly. If it's a directory, all files
        within that directory (and its subdirectories) are added.

        Args:
            path (str | Path): The file or directory path to add.
        """
        path = Path(path)

        if path.is_file():
            normalized = self._normalized_path(path)
            self.files_uploaded[normalized] = False
            logger.debug(f"Added file to record: {path}")
        elif path.is_dir():
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    normalized = self._normalized_path(file_path)
                    self.files_uploaded[normalized] = False
                    logger.debug(f"Added file to record from directory: {file_path}")
        else:
            logger.warning(f"Path '{path}' is neither a file nor a directory.")

        return self

    def mark_uploaded(self, file_path: str | Path) -> "LocalRecord":
        """
        Marks a specific file in the record as uploaded.

        Args:
            file_path (str | Path): The path of the file to mark as uploaded.
        """
        normalized = self._normalized_path(file_path)
        if normalized in self.files_uploaded:
            self.files_uploaded[normalized] = True
            logger.debug(f"Marked file as uploaded: {normalized}")
        else:
            logger.warning(f"Tried to mark non-existent file as uploaded: {normalized}")

        return self

    def all_files_uploaded(self) -> bool:
        """
        Returns True if all tracked files have been uploaded.
        """
        all_uploaded = all(self.files_uploaded.values())
        logger.debug(f"All files uploaded for record '{self.identifier}': {all_uploaded}")
        return all_uploaded

    def to_dict(self) -> dict:
        """
        Serialize all fields into a dictionary.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LocalRecord":
        """
        Reconstruct a LocalRecord from a dictionary.
        """
        return cls(**data)
