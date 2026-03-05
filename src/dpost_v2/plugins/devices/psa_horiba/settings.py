"""Settings profile for concrete V2 psa_horiba plugin."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.plugins.devices._device_template.settings import (
    DevicePluginSettings,
    validate_device_plugin_settings,
)


def validate_psa_horiba_settings(
    raw_settings: Mapping[str, Any],
) -> DevicePluginSettings:
    """Validate settings for concrete psa_horiba plugin."""
    return validate_device_plugin_settings(
        raw_settings,
        profile_overrides={
            "plugin_id": "psa_horiba",
            "source_extensions": (".csv", ".tsv", ".ngb"),
            "strict_unknown_keys": False,
        },
    )
