"""Dataclasses that describe all configurable behaviours for PCs and devices."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Pattern, Sequence
import os
import re

__all__ = [
    "PathSettings",
    "NamingSettings",
    "StabilityOverride",
    "WatcherSettings",
    "SessionSettings",
    "DeviceMetadata",
    "DeviceFileSelectors",
    "ContentMarkers",
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
    return re.compile(r"^(?!.*\.\.)(?!\.)([A-Za-z]+)-[A-Za-z]+-[A-Za-z0-9_ ]{1,30}(?<!\.)$")


def _default_temp_patterns() -> tuple[str, ...]:
    return (".tmp", ".part", ".crdownload", ".~", "-journal")


def _default_temp_folder_regex() -> Pattern[str]:
    return re.compile(r"\.[A-Za-z0-9]{6}$")


def _normalize_suffix(value: str) -> str:
    value = value.strip().lower()
    if not value:
        return value
    if not value.startswith("."):
        return f".{value}"
    return value


def _normalize_segment(value: str) -> str:
    return value.strip().lower()


@dataclass(slots=True)
class PathSettings:
    """Centralizes the filesystem locations the watchdog uses for IO and caching."""
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
    """
    Defines how file and record identifiers are structured across the app.
    Needs to be fully resolved as it currently clashes with settings in config/constants.py.
    """
    id_separator: str = "-"
    file_separator: str = "_"
    filename_pattern: Pattern[str] = field(default_factory=_default_filename_pattern, repr=False)


@dataclass(slots=True)
class StabilityOverride:
    """Allows devices to override the default file stability rules for specific items."""
    suffixes: tuple[str, ...] = ()
    folders: tuple[str, ...] = ()
    poll_seconds: Optional[float] = None
    stable_cycles: Optional[int] = None
    max_wait_seconds: Optional[float] = None

    def __post_init__(self) -> None:
        suffixes = tuple(
            normalized for normalized in (_normalize_suffix(value) for value in self.suffixes) if normalized
        )
        folders = tuple(
            normalized for normalized in (_normalize_segment(value) for value in self.folders) if normalized
        )
        object.__setattr__(self, "suffixes", suffixes)
        object.__setattr__(self, "folders", folders)

    def matches(self, path: Path) -> bool:
        lower_name = path.name.lower()
        if self.folders and lower_name in self.folders:
            return True
        if self.suffixes:
            if any(lower_name.endswith(suffix) for suffix in self.suffixes):
                return True
        return False


@dataclass(slots=True)
class WatcherSettings:
    """Configures how aggressively the watchdog polls and stabilizes discovered files."""
    poll_seconds: float = 1.0
    max_wait_seconds: float = 60.0
    stable_cycles: int = 3
    temp_patterns: tuple[str, ...] = field(default_factory=_default_temp_patterns)
    temp_folder_regex: Pattern[str] = field(default_factory=_default_temp_folder_regex, repr=False)
    sentinel_name: Optional[str] = None
    # Optional grace period to tolerate disappear/reappear (e.g., Office safe-save) before rejecting
    reappear_window_seconds: float = 0.0
    stability_overrides: tuple[StabilityOverride, ...] = field(default_factory=tuple, repr=False)

    def __post_init__(self) -> None:
        overrides = self.stability_overrides
        if not overrides:
            object.__setattr__(self, "stability_overrides", tuple())
            return
        if isinstance(overrides, StabilityOverride):
            overrides = (overrides,)
        normalized: list[StabilityOverride] = []
        for override in overrides:
            if isinstance(override, StabilityOverride):
                normalized.append(override)
            elif isinstance(override, Mapping):
                normalized.append(StabilityOverride(**override))
            else:
                raise TypeError(
                    "WatcherSettings.stability_overrides must contain StabilityOverride instances or mapping definitions"
                )
        object.__setattr__(self, "stability_overrides", tuple(normalized))


@dataclass(slots=True)
class SessionSettings:
    """Holds per-device session timing rules such as inactivity timeouts."""
    timeout_seconds: int = 300


@dataclass(slots=True)
class BatchSettings:
    """Configures device batch aggregation and timing rules."""
    ttl_seconds: int = 1800  # Time-to-live for batch aggregation (default: 30 min)
    max_batch_size: int = 100  # Maximum files per batch
    flush_on_session_end: bool = True  # Whether to flush incomplete batches on session end


@dataclass(slots=True)
class DeviceMetadata:
    """Captures identifiers and descriptions needed to register device output in Kadi."""
    user_kadi_id: str = "undefined-device-user"
    user_persistent_id: int = -1
    record_kadi_id: str = "udr_01"
    record_persistent_id: int = -1
    device_abbr: str = "GENERIC"
    record_tags: tuple[str, ...] = ("Generic Tag",)
    default_record_description: str = (
        "No description set. Override `default_record_description` in device metadata."
    )


@dataclass(frozen=True, slots=True)
class ContentMarkers:
    """Content fingerprinting markers for probe_file method."""
    positive: frozenset[str] = field(default_factory=frozenset)
    filename_patterns: tuple[str, ...] = ()
    base_confidence: float = 0.55
    confidence_per_hit: float = 0.15
    max_confidence: float = 0.95


@dataclass(slots=True)
class DeviceFileSelectors:
    """Filters which files and folders belong to a device when scanning the watch directory."""
    native_extensions: frozenset[str] = field(default_factory=frozenset)
    exported_extensions: frozenset[str] = field(default_factory=frozenset)
    allowed_extensions: frozenset[str] = field(default_factory=frozenset)
    allowed_folder_contents: frozenset[str] = field(default_factory=frozenset)
    file_encoding: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        # Normalize incoming sets to lowercase
        native = frozenset(ext.lower() for ext in self.native_extensions)
        exported = frozenset(ext.lower() for ext in self.exported_extensions)
        allowed = frozenset(ext.lower() for ext in self.allowed_extensions)
        folder = frozenset(ext.lower() for ext in self.allowed_folder_contents)
        encoding = frozenset(ext.lower() for ext in self.file_encoding)

        # Persist normalized values back
        self.native_extensions = native
        self.exported_extensions = exported
        # Respect explicitly provided allowed_extensions by unioning
        self.allowed_extensions = frozenset(native | exported | allowed)
        self.allowed_folder_contents = folder
        # Preserve provided encodings; if empty and you intended to mirror folder contents, do that in builder code
        self.file_encoding = encoding


@dataclass(slots=True)
class DeviceConfig:
    """Aggregates the knobs that tailor the watchdog to a specific instrument."""
    identifier: str
    metadata:   DeviceMetadata      = field(default_factory=DeviceMetadata)
    files:      DeviceFileSelectors = field(default_factory=DeviceFileSelectors)
    markers:    ContentMarkers      = field(default_factory=ContentMarkers)
    batch:      BatchSettings       = field(default_factory=BatchSettings)
    session:    SessionSettings     = field(default_factory=SessionSettings)
    watcher:    WatcherSettings     = field(default_factory=WatcherSettings)
    # Arbitrary plugin-specific settings (kept generic to avoid polluting the
    # core schema). Device plugins should namespace keys to avoid collisions.
    extra:      dict[str, object]   = field(default_factory=dict)

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
        # If unrestricted (no allowed extensions configured), match any file
        if not self.files.allowed_extensions:
            return True
        return path.suffix.lower() in self.files.allowed_extensions


@dataclass(slots=True)
class PCConfig:
    """
    Top-level configuration describing a workstation and its active device plugins. 
    Currently defines the PC identity and which device plugins are active.
    But may find other uses in future.
    """
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
