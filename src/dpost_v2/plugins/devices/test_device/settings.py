"""Settings profile for concrete V2 test-device plugin."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.plugins.devices._device_template.settings import (
    DevicePluginSettings,
    validate_device_plugin_settings,
)


def validate_test_device_settings(raw_settings: Mapping[str, Any]) -> DevicePluginSettings:
    """Validate settings for the concrete test-device plugin."""
    return validate_device_plugin_settings(
        raw_settings,
        profile_overrides={
            "plugin_id": "test_device",
            "source_extensions": (".csv", ".txt"),
            "strict_unknown_keys": False,
        },
    )

