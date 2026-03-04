"""Typed settings model and validation helpers for template device plugins."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


class DevicePluginSettingsError(ValueError):
    """Base exception for template device settings validation."""


class DevicePluginSettingsMissingKeyError(DevicePluginSettingsError):
    """Raised when a required settings key is missing."""


class DevicePluginSettingsValidationError(DevicePluginSettingsError):
    """Raised when a settings value has invalid type or value."""


class DevicePluginSettingsUnknownKeyError(DevicePluginSettingsError):
    """Raised when strict mode receives unknown settings keys."""


class DevicePluginSettingsOverrideError(DevicePluginSettingsError):
    """Raised when override values conflict with base settings."""


@dataclass(frozen=True, slots=True)
class DevicePluginSettings:
    """Immutable normalized settings for a device plugin."""

    plugin_id: str
    source_extensions: tuple[str, ...]
    strict_unknown_keys: bool
    extra: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.plugin_id, str) or not self.plugin_id.strip():
            raise DevicePluginSettingsValidationError(
                "plugin_id must be a non-empty string"
            )
        normalized_extensions: list[str] = []
        for extension in self.source_extensions:
            if not isinstance(extension, str) or not extension.strip():
                raise DevicePluginSettingsValidationError(
                    "source_extensions entries must be non-empty strings"
                )
            token = extension.strip().lower()
            if not token.startswith("."):
                raise DevicePluginSettingsValidationError(
                    "source_extensions entries must start with '.'"
                )
            normalized_extensions.append(token)
        object.__setattr__(self, "source_extensions", tuple(normalized_extensions))
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))


def validate_device_plugin_settings(
    raw_settings: Mapping[str, Any],
    *,
    profile_overrides: Mapping[str, Any] | None = None,
) -> DevicePluginSettings:
    """Validate and normalize template device plugin settings."""
    if not isinstance(raw_settings, Mapping):
        raise DevicePluginSettingsValidationError("raw_settings must be a mapping")
    merged: dict[str, Any] = {
        "plugin_id": "device.template",
        "source_extensions": (".dat", ".txt"),
        "strict_unknown_keys": True,
    }
    merged.update(dict(raw_settings))

    if profile_overrides is not None:
        if not isinstance(profile_overrides, Mapping):
            raise DevicePluginSettingsOverrideError(
                "profile_overrides must be a mapping"
            )
        merged.update(dict(profile_overrides))

    strict_unknown_keys = bool(merged.get("strict_unknown_keys", True))
    known_keys = {"plugin_id", "source_extensions", "strict_unknown_keys"}
    unknown_keys = sorted(set(merged) - known_keys)
    if strict_unknown_keys and unknown_keys:
        raise DevicePluginSettingsUnknownKeyError(
            f"unknown settings keys: {', '.join(unknown_keys)}"
        )

    plugin_id = merged.get("plugin_id")
    if not isinstance(plugin_id, str) or not plugin_id.strip():
        raise DevicePluginSettingsMissingKeyError("plugin_id is required")

    source_extensions = merged.get("source_extensions", ())
    if isinstance(source_extensions, str):
        source_extensions = (source_extensions,)
    if not isinstance(source_extensions, tuple | list):
        raise DevicePluginSettingsValidationError(
            "source_extensions must be a sequence of extension tokens"
        )

    extras = {key: merged[key] for key in unknown_keys}
    return DevicePluginSettings(
        plugin_id=plugin_id.strip(),
        source_extensions=tuple(source_extensions),
        strict_unknown_keys=strict_unknown_keys,
        extra=extras,
    )

