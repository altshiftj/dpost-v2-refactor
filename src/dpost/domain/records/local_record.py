"""Domain entity capturing record metadata and upload progress."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, fields as dc_fields
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

_DEFAULT_ID_SEPARATOR = "-"
_KNOWN_ID_SEPARATORS: tuple[str, ...] = ("-", ":", "|")


def _resolve_id_separator(identifier: str, preferred: str) -> str:
    """Choose an identifier separator from explicit preference or identifier shape."""
    if preferred and identifier.count(preferred) >= 3:
        return preferred
    for candidate in _KNOWN_ID_SEPARATORS:
        if candidate == preferred:
            continue
        if identifier.count(candidate) >= 3:
            return candidate
    return preferred or _DEFAULT_ID_SEPARATOR


@dataclass
class LocalRecord:
    """
    Domain record entity that tracks metadata, upload flags, and force-upload state.
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
    files_require_force: Set[str] = field(
        default_factory=set, repr=False, compare=False
    )

    # Transient sync defaults (not persisted)
    default_description: Optional[str] = field(default=None, repr=False, compare=False)
    default_tags: List[str] = field(default_factory=list, repr=False, compare=False)
    id_separator: str = field(default=_DEFAULT_ID_SEPARATOR, repr=False, compare=False)

    def __post_init__(self):
        """Parse identity segments from identifier using configured/detected separator."""
        id_separator = _resolve_id_separator(self.identifier, self.id_separator)
        parts = self.identifier.split(id_separator)
        if len(parts) >= 4:
            self.device_type = parts[0].lower()
            self.user = parts[1].lower()
            self.institute = parts[2].lower()
            if self.sample_name == "null":
                self.sample_name = id_separator.join(parts[3:])
        else:
            logger.warning(
                "Identifier '%s' does not conform to expected format.",
                self.identifier,
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
            logger.warning("Path '%s' is neither a file nor a directory.", path)
        return self

    def _register_file(self, file_path: Path) -> None:
        normalized = self._normalized_path(file_path)
        previous_status = self.files_uploaded.get(normalized)
        self.files_uploaded[normalized] = False
        if previous_status:
            self.files_require_force.add(normalized)
        elif previous_status is None:
            self.files_require_force.discard(normalized)
        logger.debug("Added file to record: %s", file_path)

    def mark_uploaded(self, file_path: str | Path) -> "LocalRecord":
        normalized = self._normalized_path(file_path)
        if normalized in self.files_uploaded:
            self.files_uploaded[normalized] = True
            self.files_require_force.discard(normalized)
            logger.debug("Marked file as uploaded: %s", normalized)
        else:
            logger.warning(
                "Tried to mark non-existent file as uploaded: %s", normalized
            )
        return self

    def all_files_uploaded(self) -> bool:
        all_uploaded = all(self.files_uploaded.values())
        logger.debug(
            "All files uploaded for record '%s': %s", self.identifier, all_uploaded
        )
        return all_uploaded

    def mark_record_unsynced(self) -> "LocalRecord":
        for key in list(self.files_uploaded.keys()):
            self.files_uploaded[key] = False
        self.files_require_force.update(self.files_uploaded.keys())
        self.is_in_db = False
        logger.debug("Marked record '%s' and its files as unsynced.", self.identifier)
        return self

    def mark_file_as_unsynced(self, filename) -> None:
        normalized = self._normalized_path(filename)
        if normalized in self.files_uploaded:
            self.files_uploaded[normalized] = False
            self.files_require_force.add(normalized)
            logger.debug("Marked file as unsynced: %s", normalized)
        else:
            logger.warning(
                "Tried to mark non-existent file as unsynced: %s", normalized
            )
        self.is_in_db = False

    def to_dict(self) -> dict:
        """Serialize LocalRecord to plain dict while excluding transient fields."""
        data: dict = {}
        for f in dc_fields(self):
            if f.name in ("default_description", "default_tags", "id_separator"):
                continue
            value = getattr(self, f.name)
            if f.name == "files_require_force":
                value = list(value)
            data[f.name] = value
        return data

    @classmethod
    def from_dict(
        cls,
        data: dict,
        id_separator: str = _DEFAULT_ID_SEPARATOR,
    ) -> "LocalRecord":
        """Build LocalRecord from persisted dict payload."""
        payload = dict(data)
        force_values = payload.get("files_require_force") or []
        if not isinstance(force_values, set):
            payload["files_require_force"] = set(force_values)
        payload.setdefault("id_separator", id_separator)
        return cls(**payload)
