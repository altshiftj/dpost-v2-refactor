"""Settings profile for concrete V2 rhe_kinexus plugin."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.plugins.devices._device_template.settings import (
    DevicePluginSettings,
    validate_device_plugin_settings,
)


def validate_rhe_kinexus_settings(raw_settings: Mapping[str, Any]) -> DevicePluginSettings:
    """Validate settings for concrete rhe_kinexus plugin."""
    return validate_device_plugin_settings(
        raw_settings,
        profile_overrides={
            "plugin_id": "rhe_kinexus",
            "source_extensions": ('.csv', '.rdf'),
            "strict_unknown_keys": False,
        },
    )
