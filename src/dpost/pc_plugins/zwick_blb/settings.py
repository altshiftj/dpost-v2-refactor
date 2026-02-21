"""PC configuration for the dpost Zwick BLB workstation plugin."""

from __future__ import annotations

from dpost.application.config import PCConfig


def build_config() -> PCConfig:
    """Return the Zwick BLB PC configuration."""
    return PCConfig(
        identifier="zwick_blb",
        active_device_plugins=("utm_zwick",),
    )
