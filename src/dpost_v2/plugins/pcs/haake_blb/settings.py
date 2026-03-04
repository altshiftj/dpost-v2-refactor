"""Settings profile for concrete V2 haake_blb PC plugin."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.plugins.pcs._pc_template.settings import (
    PcPluginSettings,
    validate_pc_plugin_settings,
)


def validate_haake_blb_settings(raw_settings: Mapping[str, Any]) -> PcPluginSettings:
    """Validate settings for concrete haake_blb PC plugin."""
    return validate_pc_plugin_settings(
        raw_settings,
        profile_overrides={
            "endpoint": "https://haake_blb.pc.invalid/api",
            "workspace_id": "haake_blb",
            "upload_mode": "immediate",
            "strict_unknown_keys": False,
            "active_device_plugins": ("extr_haake",),
        },
    )
