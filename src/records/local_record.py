from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict

from src.config.settings import ID_SEP
from src.app.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class LocalRecord:
    """
    A dataclass that represents a local record, tracking its unique identifiers,
    name, database status, and associated files.
    
    Expanded with additional sync information:
      - user: The user part extracted from the identifier.
      - institute: The institute part extracted from the identifier.
      - sample_name: The sample name part extracted from the identifier.
    
    Attributes:
        identifier (str): A concise unique identifier for the record (e.g. "usr-inst-sample").
        name (str): The record title.
        datatype (str): The type of data (e.g. "tif").
        date (str): The creation date (yyyymmdd format).
        is_in_db (bool): Flag indicating whether the record is uploaded.
        files_uploaded (Dict[str, bool]): Mapping of file paths to upload status.
        user (str): The user portion from the identifier.
        institute (str): The institute portion from the identifier.
        sample_name (str): The sample name portion from the identifier.
    """
    identifier: str = "null"
    user: str = "null"
    institute: str = "null"
    sample_name: str = "null"
    datatype: str = "null"
    date: str = "null"
    is_in_db: bool = False
    files_uploaded: Dict[str, bool] = field(default_factory=dict)

    def __post_init__(self):
        """
        Extracts additional sync info from the identifier.
        Expects identifier to be of format 'user-inst-sample'.
        """
        parts = self.identifier.split(ID_SEP)
        if len(parts) >= 3:
            self.user = parts[1].lower()
            self.institute = parts[2].lower()
            # The remainder (possibly including extra hyphens) is treated as the sample name.
            self.sample_name = ID_SEP.join(parts[3:])
        else:
            logger.warning(f"Identifier '{self.identifier}' does not conform to expected format.")

    def _normalized_path(self, path: str | Path) -> str:
        """
        Converts the input path to a fully resolved absolute path string.
        """
        return str(Path(path).resolve())

    def add_item(self, path: str | Path) -> "LocalRecord":
        """
        Adds a file or directory to the record's `files_uploaded` dictionary.
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
        Marks a specific file as uploaded.
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
        Returns True if all files have been uploaded.
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
