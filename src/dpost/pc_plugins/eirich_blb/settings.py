"""PC configuration for the dpost EIRICH BLB workstation plugin."""

from __future__ import annotations

from dpost.application.config import PCConfig


def build_config() -> PCConfig:
    """Return the EIRICH BLB PC configuration."""
    return PCConfig(
        identifier="eirich_blb",
        active_device_plugins=("rmx_eirich_el1", "rmx_eirich_r01"),
    )
