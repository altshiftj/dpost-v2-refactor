"""Typed settings and normalization helpers for template PC plugins."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


class PcPluginSettingsError(ValueError):
    """Base exception for template PC settings validation."""


class PcPluginSettingsMissingKeyError(PcPluginSettingsError):
    """Raised when required PC settings are missing."""


class PcPluginSettingsValidationError(PcPluginSettingsError):
    """Raised when a PC settings value is invalid."""


class PcPluginSettingsModeError(PcPluginSettingsError):
    """Raised when upload mode token is unsupported."""


class PcPluginSettingsOverrideError(PcPluginSettingsError):
    """Raised when strict unknown-key policy is violated."""


@dataclass(frozen=True, slots=True)
class PcPluginSettings:
    """Immutable normalized settings for template PC plugin runtime hooks."""

    endpoint: str
    workspace_id: str
    upload_mode: str
    api_token: str | None
    strict_unknown_keys: bool
    extra: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.endpoint, str) or not self.endpoint.strip():
            raise PcPluginSettingsMissingKeyError("endpoint is required")
        if not isinstance(self.workspace_id, str) or not self.workspace_id.strip():
            raise PcPluginSettingsMissingKeyError("workspace_id is required")
        if self.upload_mode not in {"immediate", "deferred"}:
            raise PcPluginSettingsModeError(
                "upload_mode must be 'immediate' or 'deferred'"
            )
        object.__setattr__(self, "endpoint", self.endpoint.strip())
        object.__setattr__(self, "workspace_id", self.workspace_id.strip())
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def redacted(self) -> Mapping[str, Any]:
        """Return diagnostics-safe settings view with secrets removed."""
        return MappingProxyType(
            {
                "endpoint": self.endpoint,
                "workspace_id": self.workspace_id,
                "upload_mode": self.upload_mode,
                "api_token": "***" if self.api_token else None,
                "strict_unknown_keys": self.strict_unknown_keys,
            }
        )


def validate_pc_plugin_settings(
    raw_settings: Mapping[str, Any],
    *,
    profile_overrides: Mapping[str, Any] | None = None,
) -> PcPluginSettings:
    """Validate and normalize template PC plugin settings payload."""
    if not isinstance(raw_settings, Mapping):
        raise PcPluginSettingsValidationError("raw_settings must be a mapping")

    merged: dict[str, Any] = {
        "endpoint": "https://example.invalid/api",
        "workspace_id": "workspace-default",
        "upload_mode": "immediate",
        "api_token": None,
        "strict_unknown_keys": True,
    }
    merged.update(dict(raw_settings))
    if profile_overrides is not None:
        if not isinstance(profile_overrides, Mapping):
            raise PcPluginSettingsOverrideError("profile_overrides must be a mapping")
        merged.update(dict(profile_overrides))

    strict_unknown_keys = bool(merged.get("strict_unknown_keys", True))
    known_keys = {
        "endpoint",
        "workspace_id",
        "upload_mode",
        "api_token",
        "strict_unknown_keys",
    }
    unknown = sorted(set(merged) - known_keys)
    if strict_unknown_keys and unknown:
        raise PcPluginSettingsOverrideError(
            f"unknown settings keys: {', '.join(unknown)}"
        )

    extras = {key: merged[key] for key in unknown}
    return PcPluginSettings(
        endpoint=str(merged.get("endpoint", "")),
        workspace_id=str(merged.get("workspace_id", "")),
        upload_mode=str(merged.get("upload_mode", "")),
        api_token=(
            str(merged["api_token"])
            if merged.get("api_token") not in {None, ""}
            else None
        ),
        strict_unknown_keys=strict_unknown_keys,
        extra=extras,
    )

