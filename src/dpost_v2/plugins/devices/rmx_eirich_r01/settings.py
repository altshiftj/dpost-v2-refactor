"""Settings profile for concrete V2 rmx_eirich_r01 plugin."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.plugins.devices._device_template.settings import (
    DevicePluginSettings,
    validate_device_plugin_settings,
)


def validate_rmx_eirich_r01_settings(
    raw_settings: Mapping[str, Any],
) -> DevicePluginSettings:
    """Validate settings for concrete rmx_eirich_r01 plugin."""
    return validate_device_plugin_settings(
        raw_settings,
        profile_overrides={
            "plugin_id": "rmx_eirich_r01",
            "source_extensions": (".txt",),
            "strict_unknown_keys": False,
        },
    )
