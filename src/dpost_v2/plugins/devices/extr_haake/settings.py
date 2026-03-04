"""Settings profile for concrete V2 extr_haake plugin."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.plugins.devices._device_template.settings import (
    DevicePluginSettings,
    validate_device_plugin_settings,
)


def validate_extr_haake_settings(
    raw_settings: Mapping[str, Any],
) -> DevicePluginSettings:
    """Validate settings for concrete extr_haake plugin."""
    return validate_device_plugin_settings(
        raw_settings,
        profile_overrides={
            "plugin_id": "extr_haake",
            "source_extensions": (".xlsx", ".xls", ".xlsm"),
            "strict_unknown_keys": False,
        },
    )
