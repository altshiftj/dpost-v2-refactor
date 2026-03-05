"""Typed startup settings model and normalization helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping


class SettingsError(ValueError):
    """Base class for startup settings normalization errors."""


class SettingsNormalizationError(SettingsError):
    """Raised when mode/profile normalization fails."""


class SettingsPathError(SettingsError):
    """Raised when path normalization fails."""


class SettingsRangeError(SettingsError):
    """Raised when numeric settings violate allowed bounds."""


class SettingsShapeError(SettingsError):
    """Raised when required settings blocks are missing."""


@dataclass(frozen=True)
class RuntimeSettings:
    """Runtime startup mode and profile settings."""

    mode: str
    profile: str | None


@dataclass(frozen=True)
class PathSettings:
    """Normalized path settings used by runtime startup."""

    root: str
    watch: str
    dest: str
    staging: str


@dataclass(frozen=True)
class NamingSettings:
    """Naming policy settings for runtime startup context."""

    prefix: str
    policy: str


@dataclass(frozen=True)
class IngestionSettings:
    """Ingestion policy settings for runtime startup context."""

    retry_limit: int
    retry_delay_seconds: float


@dataclass(frozen=True)
class SyncSettings:
    """Sync backend settings for runtime startup context."""

    backend: str
    api_token: str | None


@dataclass(frozen=True)
class UiSettings:
    """UI backend settings for runtime startup context."""

    backend: str


@dataclass(frozen=True)
class PluginPolicySettings:
    """Optional workstation policy selection used by runtime startup."""

    pc_name: str | None = None
    device_plugins: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        pc_name = _normalize_optional_string(self.pc_name)
        object.__setattr__(
            self, "pc_name", None if pc_name is None else pc_name.lower()
        )

        normalized_device_plugins: list[str] = []
        for plugin_id in self.device_plugins:
            token = _normalize_optional_string(plugin_id)
            if token is None:
                raise SettingsNormalizationError(
                    "plugins.device_plugins entries must be non-empty strings."
                )
            normalized_device_plugins.append(token.lower())
        object.__setattr__(
            self,
            "device_plugins",
            tuple(normalized_device_plugins),
        )


@dataclass(frozen=True)
class StartupSettings:
    """Aggregate startup settings consumed by bootstrap and composition."""

    runtime: RuntimeSettings
    paths: PathSettings
    naming: NamingSettings
    ingestion: IngestionSettings
    sync: SyncSettings
    ui: UiSettings
    plugins: PluginPolicySettings = field(default_factory=PluginPolicySettings)
    source_fingerprint: str | None = None

    @property
    def mode(self) -> str:
        """Return canonical runtime mode token."""
        return self.runtime.mode

    @property
    def profile(self) -> str | None:
        """Return canonical runtime profile token when configured."""
        return self.runtime.profile

    def to_dependency_payload(self) -> dict[str, Any]:
        """Convert settings to dependency resolver input payload."""
        return {
            "mode": self.mode,
            "profile": self.profile,
            "paths": {
                "root": self.paths.root,
                "watch": self.paths.watch,
                "dest": self.paths.dest,
                "staging": self.paths.staging,
            },
            "sync": {
                "backend": self.sync.backend,
                "api_token": self.sync.api_token,
            },
            "ui": {
                "backend": self.ui.backend,
            },
            "plugins": {
                "pc_name": self.plugins.pc_name,
                "device_plugins": self.plugins.device_plugins,
            },
            "backends": {
                "ui": self.ui.backend,
                "sync": self.sync.backend,
                "plugins": "builtin",
                "observability": "structured",
                "storage": "filesystem",
            },
        }


def from_raw(
    raw_config: Mapping[str, Any],
    *,
    root_hint: Path | str | None = None,
    source_fingerprint: str | None = None,
) -> StartupSettings:
    """Build immutable StartupSettings from raw validated payload."""
    mode = normalize_mode(raw_config.get("mode"))
    profile = _normalize_profile(raw_config.get("profile"))

    paths_block = _required_block(raw_config, "paths")
    ui_block = _required_block(raw_config, "ui")
    sync_block = _required_block(raw_config, "sync")
    ingestion_block = _required_block(raw_config, "ingestion")
    naming_block = _required_block(raw_config, "naming")
    plugins_block = raw_config.get("plugins") or {}
    if not isinstance(plugins_block, Mapping):
        raise SettingsShapeError("Settings block 'plugins' must be a mapping.")

    root, watch, dest, staging = normalize_paths(paths_block, root_hint=root_hint)
    retry_limit, retry_delay = normalize_retry_policy(ingestion_block)

    prefix = str(naming_block.get("prefix", "")).strip()
    if not prefix:
        raise SettingsShapeError("Settings block 'naming.prefix' is required.")

    policy = str(naming_block.get("policy", "")).strip().lower()
    if policy not in {"prefix_only", "prefix_date"}:
        raise SettingsNormalizationError(
            f"Unsupported naming policy: {naming_block.get('policy')!r}."
        )

    ui_backend = str(ui_block.get("backend", "")).strip().lower()
    if ui_backend not in {"headless", "desktop"}:
        raise SettingsNormalizationError(
            f"Unsupported ui backend: {ui_block.get('backend')!r}."
        )

    sync_backend = str(sync_block.get("backend", "")).strip().lower()
    if sync_backend not in {"noop", "kadi"}:
        raise SettingsNormalizationError(
            f"Unsupported sync backend: {sync_block.get('backend')!r}."
        )

    return StartupSettings(
        runtime=RuntimeSettings(mode=mode, profile=profile),
        paths=PathSettings(root=root, watch=watch, dest=dest, staging=staging),
        naming=NamingSettings(prefix=prefix, policy=policy),
        ingestion=IngestionSettings(
            retry_limit=retry_limit,
            retry_delay_seconds=retry_delay,
        ),
        sync=SyncSettings(
            backend=sync_backend,
            api_token=_normalize_optional_string(sync_block.get("api_token")),
        ),
        ui=UiSettings(backend=ui_backend),
        plugins=PluginPolicySettings(
            pc_name=_normalize_optional_string(plugins_block.get("pc_name")),
            device_plugins=_normalize_device_plugin_ids(
                plugins_block.get("device_plugins", ())
            ),
        ),
        source_fingerprint=source_fingerprint,
    )


def normalize_mode(raw_mode: Any) -> str:
    """Normalize runtime mode to canonical token."""
    mode = str(raw_mode or "").strip().lower()
    if mode not in {"headless", "desktop"}:
        raise SettingsNormalizationError(f"Unsupported startup mode: {raw_mode!r}.")
    return mode


def normalize_paths(
    raw_paths: Mapping[str, Any],
    *,
    root_hint: Path | str | None = None,
) -> tuple[str, str, str, str]:
    """Normalize path fields to absolute path strings."""
    root_raw = _normalize_optional_string(raw_paths.get("root"))
    if not root_raw:
        raise SettingsPathError("Settings block 'paths.root' is required.")

    root_base = Path(root_hint).resolve() if root_hint is not None else Path.cwd()
    root_path = _normalize_path(root_raw, anchor=root_base)

    watch_path = _normalize_path(
        _normalize_optional_string(raw_paths.get("watch")) or "incoming",
        anchor=root_path,
    )
    dest_path = _normalize_path(
        _normalize_optional_string(raw_paths.get("dest")) or "processed",
        anchor=root_path,
    )
    staging_path = _normalize_path(
        _normalize_optional_string(raw_paths.get("staging")) or "tmp",
        anchor=root_path,
    )
    return (
        str(root_path),
        str(watch_path),
        str(dest_path),
        str(staging_path),
    )


def normalize_retry_policy(raw_ingestion: Mapping[str, Any]) -> tuple[int, float]:
    """Normalize and validate ingestion retry settings."""
    retry_limit = int(raw_ingestion.get("retry_limit", 0))
    retry_delay = float(raw_ingestion.get("retry_delay_seconds", 0.0))

    if retry_limit < 0:
        raise SettingsRangeError(
            f"ingestion.retry_limit must be >= 0. Got {retry_limit}."
        )
    if retry_delay < 0:
        raise SettingsRangeError(
            f"ingestion.retry_delay_seconds must be >= 0. Got {retry_delay}."
        )
    return retry_limit, retry_delay


def to_redacted_dict(settings: StartupSettings) -> dict[str, Any]:
    """Render startup settings with secrets redacted for diagnostics."""
    payload = asdict(settings)
    if payload["sync"]["api_token"] is not None:
        payload["sync"]["api_token"] = "<redacted>"
    return payload


def _required_block(raw_config: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    block = raw_config.get(key)
    if not isinstance(block, Mapping):
        raise SettingsShapeError(f"Settings block '{key}' is required.")
    return block


def _normalize_path(raw_value: str, *, anchor: Path) -> Path:
    try:
        path = Path(raw_value)
    except TypeError as exc:
        raise SettingsPathError(f"Invalid path value: {raw_value!r}.") from exc

    if path.is_absolute():
        return path.resolve()
    return (anchor / path).resolve()


def _normalize_profile(raw_profile: Any) -> str | None:
    value = _normalize_optional_string(raw_profile)
    if not value:
        return None
    return value.lower()


def _normalize_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_device_plugin_ids(value: Any) -> tuple[str, ...]:
    if value in {None, ""}:
        return ()
    if not isinstance(value, tuple | list):
        raise SettingsNormalizationError(
            "plugins.device_plugins must be a sequence of plugin ids."
        )
    normalized: list[str] = []
    for plugin_id in value:
        token = _normalize_optional_string(plugin_id)
        if token is None:
            raise SettingsNormalizationError(
                "plugins.device_plugins entries must be non-empty strings."
            )
        normalized.append(token.lower())
    return tuple(normalized)
