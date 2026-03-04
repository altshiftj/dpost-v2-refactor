"""Settings profile for concrete V2 utm_zwick plugin."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.plugins.devices._device_template.settings import (
    DevicePluginSettings,
    validate_device_plugin_settings,
)


def validate_utm_zwick_settings(raw_settings: Mapping[str, Any]) -> DevicePluginSettings:
    """Validate settings for concrete utm_zwick plugin."""
    return validate_device_plugin_settings(
        raw_settings,
        profile_overrides={
            "plugin_id": "utm_zwick",
            "source_extensions": ('.xlsx', '.zs2'),
            "strict_unknown_keys": False,
        },
    )
