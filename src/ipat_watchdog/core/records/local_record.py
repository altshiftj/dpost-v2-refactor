"""Local persistence model capturing record metadata and upload progress."""

from pathlib import Path
from dataclasses import dataclass, field, fields as dc_fields
from typing import Dict, List, Optional, Set

from ipat_watchdog.core.config import current
from ipat_watchdog.core.logging.logger import setup_logger

logger = setup_logger(__name__)


def _id_separator() -> str:
    """Resolve record identifier separator from active config."""
    try:
        return current().id_separator
    except RuntimeError:
        return "-"


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
    files_require_force: Set[str] = field(default_factory=set, repr=False, compare=False)

    # Transient sync defaults (not persisted)
    default_description: Optional[str] = field(default=None, repr=False, compare=False)
    default_tags: List[str] = field(default_factory=list, repr=False, compare=False)

    def __post_init__(self):
        """
        Extracts additional sync info from the identifier using the device's configured ID separator.
        """
        id_separator = _id_separator()
        parts = self.identifier.split(id_separator)
        if len(parts) >= 4:
            self.device_type = parts[0].lower()
            self.user = parts[1].lower()
            self.institute = parts[2].lower()
            if self.sample_name == "null":
                self.sample_name = id_separator.join(parts[3:])
        else:
            logger.warning(
                f"Identifier '{self.identifier}' does not conform to expected format."
            )

    def _normalized_path(self, path: str | Path) -> str:
        return str(Path(path).resolve())

    def add_item(self, path: str | Path) -> "LocalRecord":
        path = Path(path)
        if path.is_file():
            self._register_file(path)
        elif path.is_dir():
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    self._register_file(file_path)
        else:
            logger.warning(f"Path '{path}' is neither a file nor a directory.")
        return self

    def _register_file(self, file_path: Path) -> None:
        normalized = self._normalized_path(file_path)
        previous_status = self.files_uploaded.get(normalized)
        self.files_uploaded[normalized] = False
        if previous_status:
            self.files_require_force.add(normalized)
        elif previous_status is None:
            self.files_require_force.discard(normalized)
        logger.debug(f"Added file to record: {file_path}")

    def mark_uploaded(self, file_path: str | Path) -> "LocalRecord":
        normalized = self._normalized_path(file_path)
        if normalized in self.files_uploaded:
            self.files_uploaded[normalized] = True
            self.files_require_force.discard(normalized)
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

    def mark_record_unsynced(self) -> "LocalRecord":
        for key in list(self.files_uploaded.keys()):
            self.files_uploaded[key] = False
        self.files_require_force.update(self.files_uploaded.keys())
        self.is_in_db = False
        logger.debug(f"Marked record '{self.identifier}' and its files as unsynced.")
        return self

    def mark_file_as_unsynced(self, filename) -> None:
        normalized = self._normalized_path(filename)
        if normalized in self.files_uploaded:
            self.files_uploaded[normalized] = False
            self.files_require_force.add(normalized)
            logger.debug(f"Marked file as unsynced: {normalized}")
        else:
            logger.warning(f"Tried to mark non-existent file as unsynced: {normalized}")
        self.is_in_db = False

    def to_dict(self) -> dict:
        # Exclude transient fields from persistence
        data: dict = {}
        for f in dc_fields(self):
            if f.name in ("default_description", "default_tags"):
                continue
            value = getattr(self, f.name)
            if f.name == "files_require_force":
                value = list(value)
            data[f.name] = value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "LocalRecord":
        payload = dict(data)
        force_values = payload.get("files_require_force") or []
        if not isinstance(force_values, set):
            payload["files_require_force"] = set(force_values)
        return cls(**payload)
