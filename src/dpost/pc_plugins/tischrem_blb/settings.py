"""PC configuration for the dpost TISCHREM BLB workstation plugin."""

from __future__ import annotations

from dpost.application.config import PCConfig


def build_config() -> PCConfig:
    """Return the TISCHREM BLB PC configuration."""
    return PCConfig(
        identifier="tischrem_blb",
        active_device_plugins=("sem_phenomxl2",),
    )
