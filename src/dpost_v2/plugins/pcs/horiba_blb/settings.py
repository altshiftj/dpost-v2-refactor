"""Settings profile for concrete V2 horiba_blb PC plugin."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.plugins.pcs._pc_template.settings import (
    PcPluginSettings,
    validate_pc_plugin_settings,
)


def validate_horiba_blb_settings(raw_settings: Mapping[str, Any]) -> PcPluginSettings:
    """Validate settings for concrete horiba_blb PC plugin."""
    return validate_pc_plugin_settings(
        raw_settings,
        profile_overrides={
            "endpoint": "https://horiba_blb.pc.invalid/api",
            "workspace_id": "horiba_blb",
            "upload_mode": "immediate",
            "strict_unknown_keys": False,
            "active_device_plugins": ('psa_horiba', 'dsv_horiba'),
        },
    )
