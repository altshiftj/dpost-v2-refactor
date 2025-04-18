from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict

from ipat_watchdog.config.settings_store import SettingsStore
from ipat_watchdog.config.settings_base import BaseSettings
from ipat_watchdog.app.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class LocalRecord:
    """
    A dataclass that represents a local record, tracking its unique identifiers,
    name, database status, and associated files.
    """

    identifier: str = "null"
    device_type: str = "null"
    user: str = "null"
    institute: str = "null"
    sample_name: str = "null"
    datatype: str = "null"
    date: str = "null"
    is_in_db: bool = False
    files_uploaded: Dict[str, bool] = field(default_factory=dict)

    def __post_init__(self):
        """
        Extracts additional sync info from the identifier using the device's configured ID separator.
        """
        settings: BaseSettings = SettingsStore.get()
        sep = settings.ID_SEP

        parts = self.identifier.split(sep)
        if len(parts) >= 4:
            self.device_type = parts[0].lower()
            self.user = parts[1].lower()
            self.institute = parts[2].lower()
            if self.sample_name == "null":
                self.sample_name = sep.join(parts[3:])
        else:
            logger.warning(
                f"Identifier '{self.identifier}' does not conform to expected format."
            )

    def _normalized_path(self, path: str | Path) -> str:
        return str(Path(path).resolve())

    def add_item(self, path: str | Path) -> "LocalRecord":
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
        normalized = self._normalized_path(file_path)
        if normalized in self.files_uploaded:
            self.files_uploaded[normalized] = True
            logger.debug(f"Marked file as uploaded: {normalized}")
        else:
            logger.warning(f"Tried to mark non-existent file as uploaded: {normalized}")
        return self

    def all_files_uploaded(self) -> bool:
        all_uploaded = all(self.files_uploaded.values())
        logger.debug(
            f"All files uploaded for record '{self.identifier}': {all_uploaded}"
        )
        return all_uploaded

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LocalRecord":
        return cls(**data)
