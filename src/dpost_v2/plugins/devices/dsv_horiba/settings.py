"""Settings profile for concrete V2 dsv_horiba plugin."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.plugins.devices._device_template.settings import (
    DevicePluginSettings,
    validate_device_plugin_settings,
)


def validate_dsv_horiba_settings(
    raw_settings: Mapping[str, Any],
) -> DevicePluginSettings:
    """Validate settings for concrete dsv_horiba plugin."""
    return validate_device_plugin_settings(
        raw_settings,
        profile_overrides={
            "plugin_id": "dsv_horiba",
            "source_extensions": (".txt", ".wdb", ".wdk", ".wdp"),
            "strict_unknown_keys": False,
        },
    )
