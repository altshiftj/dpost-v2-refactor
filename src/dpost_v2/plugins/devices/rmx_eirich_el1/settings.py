"""Settings profile for concrete V2 rmx_eirich_el1 plugin."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.plugins.devices._device_template.settings import (
    DevicePluginSettings,
    validate_device_plugin_settings,
)


def validate_rmx_eirich_el1_settings(
    raw_settings: Mapping[str, Any],
) -> DevicePluginSettings:
    """Validate settings for concrete rmx_eirich_el1 plugin."""
    return validate_device_plugin_settings(
        raw_settings,
        profile_overrides={
            "plugin_id": "rmx_eirich_el1",
            "source_extensions": (".txt",),
            "strict_unknown_keys": False,
        },
    )
