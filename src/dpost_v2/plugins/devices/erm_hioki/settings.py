"""Settings profile for concrete V2 erm_hioki plugin."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.plugins.devices._device_template.settings import (
    DevicePluginSettings,
    validate_device_plugin_settings,
)


def validate_erm_hioki_settings(
    raw_settings: Mapping[str, Any],
) -> DevicePluginSettings:
    """Validate settings for concrete erm_hioki plugin."""
    return validate_device_plugin_settings(
        raw_settings,
        profile_overrides={
            "plugin_id": "erm_hioki",
            "source_extensions": (".xlsx", ".xls", ".csv"),
            "strict_unknown_keys": False,
        },
    )
