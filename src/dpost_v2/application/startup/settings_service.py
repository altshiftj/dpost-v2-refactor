"""Settings loading/merge service for startup bootstrap flow."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from dpost_v2.application.startup.settings import (
    StartupSettings,
    from_raw,
    to_redacted_dict,
)
from dpost_v2.application.startup.settings_schema import (
    SettingsSchemaError,
    validate_raw_settings,
)

_SOURCE_ORDER: tuple[str, ...] = ("defaults", "file", "environment", "cli")


class SettingsServiceError(RuntimeError):
    """Base class for startup settings service failures."""


class SettingsSourceReadError(SettingsServiceError):
    """Raised when a configured settings source cannot be read."""


class SettingsValidationError(SettingsServiceError):
    """Raised when schema validation fails for merged startup settings."""


class SettingsMergeTypeError(SettingsServiceError):
    """Raised when merge layers have incompatible value types."""


class SettingsCacheIntegrityError(SettingsServiceError):
    """Raised when cache metadata is internally inconsistent."""


class SupportsBootstrapRequest(Protocol):
    """Subset of bootstrap request fields consumed by settings service."""

    mode: str
    profile: str | None
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class SettingsLoadFailure:
    """Typed failure payload for startup settings loading."""

    stage: str
    error_type: str
    message: str
    issues: tuple[Mapping[str, str], ...] = ()


@dataclass(frozen=True)
class SettingsLoadResult:
    """Typed success/failure result consumed by bootstrap orchestration."""

    is_success: bool
    settings: StartupSettings | None = None
    provenance: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    diagnostics: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    fingerprint: str | None = None
    failure: SettingsLoadFailure | None = None


@dataclass
class SettingsCacheEntry:
    """Cache entry for settings fingerprint reuse."""

    fingerprint: str
    settings: StartupSettings | None
    diagnostics: Mapping[str, Any]
    settings_fingerprint: str | None = None


@dataclass
class SettingsCache:
    """Optional mutable cache handle reused across bootstrap calls."""

    entry: SettingsCacheEntry | None = None


def load_startup_settings(
    request: SupportsBootstrapRequest,
    *,
    root_hint: Path | str | None = None,
    sources: Mapping[str, Any] | None = None,
    cache: SettingsCache | None = None,
) -> SettingsLoadResult:
    """Load, merge, validate, and normalize startup settings."""
    integrity_issue: SettingsCacheIntegrityError | None = None
    try:
        source_payloads = _resolve_sources(
            request=request,
            explicit_sources=sources,
            root_hint=root_hint,
        )
        fingerprint = _compute_fingerprint(source_payloads)

        if cache is not None and cache.entry is not None:
            integrity_issue = _detect_cache_desync(cache.entry)
            if integrity_issue is not None:
                cache.entry = None

        if (
            cache is not None
            and cache.entry is not None
            and cache.entry.fingerprint == fingerprint
            and cache.entry.settings is not None
        ):
            diagnostics = {
                "cache_hit": True,
                "fingerprint": fingerprint,
                "redacted_settings": to_redacted_dict(cache.entry.settings),
            }
            return SettingsLoadResult(
                is_success=True,
                settings=cache.entry.settings,
                provenance=MappingProxyType({}),
                diagnostics=MappingProxyType(diagnostics),
                fingerprint=fingerprint,
            )

        merged_payload, provenance = _merge_sources(source_payloads)

        try:
            validated_payload = validate_raw_settings(merged_payload)
        except SettingsSchemaError as exc:
            raise SettingsValidationError(str(exc)) from exc

        settings = from_raw(
            validated_payload,
            root_hint=root_hint,
            source_fingerprint=fingerprint,
        )

        diagnostics = {
            "cache_hit": False,
            "fingerprint": fingerprint,
            "redacted_settings": to_redacted_dict(settings),
        }
        if integrity_issue is not None:
            diagnostics["cache_integrity_error"] = (
                f"{type(integrity_issue).__name__}: {integrity_issue}"
            )

        if cache is not None:
            cache.entry = SettingsCacheEntry(
                fingerprint=fingerprint,
                settings=settings,
                diagnostics=MappingProxyType(dict(diagnostics)),
                settings_fingerprint=settings.source_fingerprint,
            )

        return SettingsLoadResult(
            is_success=True,
            settings=settings,
            provenance=MappingProxyType(dict(provenance)),
            diagnostics=MappingProxyType(diagnostics),
            fingerprint=fingerprint,
        )
    except SettingsServiceError as exc:
        return SettingsLoadResult(
            is_success=False,
            failure=SettingsLoadFailure(
                stage="settings_service",
                error_type=type(exc).__name__,
                message=str(exc),
            ),
            diagnostics=MappingProxyType({"cache_hit": False}),
        )


def _resolve_sources(
    *,
    request: SupportsBootstrapRequest,
    explicit_sources: Mapping[str, Any] | None,
    root_hint: Path | str | None = None,
) -> dict[str, dict[str, Any]]:
    raw_sources = dict(
        explicit_sources or _default_sources_from_request(request, root_hint)
    )
    resolved: dict[str, dict[str, Any]] = {}
    for source_name in _SOURCE_ORDER:
        source_value = raw_sources.get(source_name, {})
        if callable(source_value):
            try:
                source_value = source_value(request)
            except Exception as exc:
                raise SettingsSourceReadError(
                    f"Failed reading settings source {source_name!r}."
                ) from exc

        if source_value is None:
            source_value = {}
        if not isinstance(source_value, Mapping):
            raise SettingsSourceReadError(
                f"Settings source {source_name!r} must be a mapping."
            )
        resolved[source_name] = dict(source_value)
    return resolved


def _default_sources_from_request(
    request: SupportsBootstrapRequest,
    root_hint: Path | str | None,
) -> dict[str, Mapping[str, Any]]:
    metadata_sources = request.metadata.get("settings_sources")
    normalized_mode = _normalized_settings_mode(request)
    if isinstance(metadata_sources, Mapping):
        return {
            "defaults": metadata_sources.get("defaults", {}),
            "file": metadata_sources.get("file", {}),
            "environment": metadata_sources.get("environment", {}),
            "cli": metadata_sources.get("cli", {}),
        }

    config_path = request.metadata.get("config_path")
    config_settings = _load_file_config(config_path, root_hint=root_hint)
    cli_settings: dict[str, Any] = {"mode": normalized_mode}
    if request.profile is not None:
        cli_settings["profile"] = request.profile

    return {
        "defaults": {
            "mode": normalized_mode,
            "profile": "default",
            "paths": {"root": "."},
            "ui": {"backend": "headless"},
            "sync": {"backend": "noop"},
            "ingestion": {"retry_limit": 3, "retry_delay_seconds": 1.0},
            "naming": {"prefix": "DPOST", "policy": "prefix_only"},
            "plugins": {"pc_name": None, "device_plugins": ()},
        },
        "file": config_settings,
        "environment": _load_environment_settings(os.environ),
        "cli": cli_settings,
    }


def _load_file_config(
    config_path: Any,
    *,
    root_hint: Path | str | None = None,
) -> dict[str, Any]:
    if not config_path:
        return {}
    normalized = str(config_path).strip()
    if not normalized:
        return {}

    config_file = Path(normalized)
    if not config_file.is_absolute() and root_hint is not None:
        config_file = Path(root_hint) / config_file

    if not config_file.exists():
        raise SettingsSourceReadError(f"Config file not found: {config_file!s}.")
    if not config_file.is_file():
        raise SettingsSourceReadError(f"Config path is not a file: {config_file!s}.")

    try:
        with config_file.open("r", encoding="utf-8") as config_stream:
            payload = json.load(config_stream)
    except OSError as exc:
        raise SettingsSourceReadError(
            f"Failed reading config file {config_file!s}."
        ) from exc
    except json.JSONDecodeError as exc:
        raise SettingsSourceReadError(
            f"Invalid JSON in config file {config_file!s}."
        ) from exc

    if not isinstance(payload, Mapping):
        raise SettingsSourceReadError(
            f"Config file payload must be a mapping: {config_file!s}."
        )
    return dict(payload)


def _normalized_settings_mode(request: SupportsBootstrapRequest) -> str:
    """Map launch architecture mode to a runtime settings mode token."""
    requested_mode = str(request.mode or "").strip().lower()

    if requested_mode == "v2":
        return "headless"

    return requested_mode or "headless"


def _load_environment_settings(environment: Mapping[str, str]) -> dict[str, Any]:
    plugins: dict[str, Any] = {}
    pc_name = _first_env_value(environment, "DPOST_PC_NAME", "PC_NAME")
    if pc_name is not None:
        plugins["pc_name"] = pc_name

    device_plugins = _split_env_plugin_ids(
        _first_env_value(environment, "DPOST_DEVICE_PLUGINS", "DEVICE_PLUGINS")
    )
    if device_plugins:
        plugins["device_plugins"] = device_plugins

    if not plugins:
        return {}
    return {"plugins": plugins}


def _first_env_value(environment: Mapping[str, str], *names: str) -> str | None:
    for name in names:
        candidate = str(environment.get(name, "")).strip()
        if candidate:
            return candidate
    return None


def _split_env_plugin_ids(raw_value: str | None) -> tuple[str, ...]:
    if raw_value is None:
        return ()
    tokens = [
        token.strip()
        for token in raw_value.replace(";", ",").split(",")
        if token.strip()
    ]
    return tuple(tokens)


def _merge_sources(
    source_payloads: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, str]]:
    merged: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    for source_name in _SOURCE_ORDER:
        source_payload = source_payloads[source_name]
        _deep_merge(
            target=merged,
            incoming=source_payload,
            source_name=source_name,
            provenance=provenance,
            path_prefix="",
        )
    return merged, provenance


def _deep_merge(
    *,
    target: dict[str, Any],
    incoming: Mapping[str, Any],
    source_name: str,
    provenance: dict[str, str],
    path_prefix: str,
) -> None:
    for key, value in incoming.items():
        full_path = f"{path_prefix}.{key}" if path_prefix else key
        key_exists = key in target
        existing = target.get(key)

        if isinstance(existing, dict) and isinstance(value, Mapping):
            _deep_merge(
                target=existing,
                incoming=value,
                source_name=source_name,
                provenance=provenance,
                path_prefix=full_path,
            )
            continue

        if key_exists and isinstance(existing, dict) != isinstance(value, Mapping):
            raise SettingsMergeTypeError(
                f"Incompatible settings merge at {full_path!r}: cannot merge mapping "
                "with non-mapping value."
            )

        target[key] = dict(value) if isinstance(value, Mapping) else value
        provenance[full_path] = source_name


def _compute_fingerprint(source_payloads: Mapping[str, Mapping[str, Any]]) -> str:
    canonical = {name: source_payloads[name] for name in _SOURCE_ORDER}
    serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _detect_cache_desync(
    cache_entry: SettingsCacheEntry,
) -> SettingsCacheIntegrityError | None:
    if cache_entry.settings_fingerprint is None:
        return None
    if cache_entry.settings_fingerprint == cache_entry.fingerprint:
        return None
    return SettingsCacheIntegrityError(
        "Settings cache entry fingerprint mismatch between cache metadata and "
        "stored settings fingerprint."
    )
