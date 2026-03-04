"""Settings profile for concrete V2 test PC plugin."""

from __future__ import annotations

from typing import Any, Mapping

from dpost_v2.plugins.pcs._pc_template.settings import (
    PcPluginSettings,
    validate_pc_plugin_settings,
)


def validate_test_pc_settings(raw_settings: Mapping[str, Any]) -> PcPluginSettings:
    """Validate settings for concrete test PC plugin."""
    return validate_pc_plugin_settings(
        raw_settings,
        profile_overrides={
            "endpoint": "https://pc.test.invalid/api",
            "workspace_id": "pc-test-workspace",
            "upload_mode": "immediate",
            "strict_unknown_keys": False,
        },
    )

