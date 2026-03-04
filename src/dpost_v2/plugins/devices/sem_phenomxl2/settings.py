"""Settings profile for concrete V2 sem_phenomxl2 plugin."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.plugins.devices._device_template.settings import (
    DevicePluginSettings,
    validate_device_plugin_settings,
)


def validate_sem_phenomxl2_settings(
    raw_settings: Mapping[str, Any],
) -> DevicePluginSettings:
    """Validate settings for concrete sem_phenomxl2 plugin."""
    return validate_device_plugin_settings(
        raw_settings,
        profile_overrides={
            "plugin_id": "sem_phenomxl2",
            "source_extensions": (".tiff", ".tif", ".jpeg", ".jpg"),
            "strict_unknown_keys": False,
        },
    )
