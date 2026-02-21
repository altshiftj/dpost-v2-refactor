"""PC configuration for the dpost KINEXUS BLB workstation plugin."""

from __future__ import annotations

from dpost.application.config import PCConfig


def build_config() -> PCConfig:
    """Return the KINEXUS BLB PC configuration."""
    return PCConfig(
        identifier="kinexus_blb",
        active_device_plugins=("rhe_kinexus",),
    )
