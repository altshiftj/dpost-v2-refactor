from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Pattern, Sequence
import os
import re

__all__ = [
    "PathSettings",
    "NamingSettings",
    "WatcherSettings",
    "SessionSettings",
    "DeviceMetadata",
    "DeviceFileSelectors",
    "DeviceConfig",
    "PCConfig",
]


def _default_app_dir() -> Path:
    return Path("C:/Watchdog")


def _default_user_home() -> Path:
    env_home = os.environ.get("USERPROFILE") or os.environ.get("HOME")
    return Path(env_home) if env_home else Path.home()


def _default_desktop() -> Path:
    return _default_user_home() / "Desktop"


def _default_filename_pattern() -> Pattern[str]:
    return re.compile(r"^(?!.*\\.\\.)(?!\.)([A-Za-z]+)-[A-Za-z]+-[A-Za-z0-9_ ]{1,30}+(?<!\.)$")


def _default_temp_patterns() -> tuple[str, ...]:
    return (".tmp", ".part", ".crdownload", ".~", "-journal")


def _default_temp_folder_regex() -> Pattern[str]:
    return re.compile(r"\.[A-Za-z0-9]{6}$")


@dataclass(slots=True)
class PathSettings:
    app_dir: Path = field(default_factory=_default_app_dir)
    desktop_dir: Path = field(default_factory=_default_desktop)
    watch_dir: Path = field(default_factory=lambda: _default_desktop() / "Upload")
    dest_dir: Path = field(default_factory=lambda: _default_desktop() / "Data")
    rename_dir: Path = field(default_factory=lambda: _default_desktop() / "Data" / "00_To_Rename")
    exceptions_dir: Path = field(default_factory=lambda: _default_desktop() / "Data" / "01_Exceptions")
    daily_records_json: Path = field(default_factory=lambda: _default_app_dir() / "record_persistence.json")

    def directory_list(self) -> tuple[Path, ...]:
        return (
            self.app_dir,
            self.watch_dir,
            self.dest_dir,
            self.rename_dir,
            self.exceptions_dir,
        )


@dataclass(slots=True)
class NamingSettings:
    id_separator: str = "-"
    file_separator: str = "_"
    filename_pattern: Pattern[str] = field(default_factory=_default_filename_pattern, repr=False)


@dataclass(slots=True)
class WatcherSettings:
    poll_seconds: float = 1.0
    max_wait_seconds: float = 60.0
    stable_cycles: int = 3
    temp_patterns: tuple[str, ...] = field(default_factory=_default_temp_patterns)
    temp_folder_regex: Pattern[str] = field(default_factory=_default_temp_folder_regex, repr=False)
    sentinel_name: Optional[str] = None


@dataclass(slots=True)
class SessionSettings:
    timeout_seconds: int = -1


@dataclass(slots=True)
class DeviceMetadata:
    user_kadi_id: str = "undefined-device-user"
    user_persistent_id: int = -1
    record_kadi_id: str = "udr_01"
    record_persistent_id: int = -1
    device_abbr: str = "GENERIC"
    record_tags: tuple[str, ...] = ("Generic Tag",)
    default_record_description: str = (
        "No description set. Override `default_record_description` in device metadata."
    )


@dataclass(slots=True)
class DeviceFileSelectors:
    allowed_extensions: frozenset[str] = field(default_factory=frozenset)
    allowed_folder_contents: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        self.allowed_extensions = frozenset(ext.lower() for ext in self.allowed_extensions)
        self.allowed_folder_contents = frozenset(ext.lower() for ext in self.allowed_folder_contents)


@dataclass(slots=True)
class DeviceConfig:
    identifier: str
    metadata: DeviceMetadata = field(default_factory=DeviceMetadata)
    files: DeviceFileSelectors = field(default_factory=DeviceFileSelectors)
    session: SessionSettings = field(default_factory=lambda: SessionSettings(timeout_seconds=300))
    watcher: WatcherSettings = field(default_factory=WatcherSettings)

    def matches_file(self, path_like: str | Path) -> bool:
        path = Path(path_like)
        if path.is_dir():
            if not self.files.allowed_folder_contents:
                return False
            try:
                contents = {
                    p.suffix.lower()
                    for p in path.rglob("*")
                    if p.is_file()
                }
            except FileNotFoundError:
                return False
            return bool(contents.intersection(self.files.allowed_folder_contents))
        if not self.files.allowed_extensions:
            return True
        return path.suffix.lower() in self.files.allowed_extensions


@dataclass(slots=True)
class PCConfig:
    identifier: str
    name: Optional[str] = None
    location: Optional[str] = None
    paths: PathSettings = field(default_factory=PathSettings)
    naming: NamingSettings = field(default_factory=NamingSettings)
    session: SessionSettings = field(default_factory=SessionSettings)
    watcher: WatcherSettings = field(default_factory=WatcherSettings)
    active_device_plugins: Sequence[str] = field(default_factory=tuple)

    def directory_list(self) -> tuple[Path, ...]:
        return self.paths.directory_list()
