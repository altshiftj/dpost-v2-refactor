"""PC configuration for the dpost HORIBA BLB workstation plugin."""

from __future__ import annotations

from dpost.application.config import PCConfig


def build_config() -> PCConfig:
    """Return the HORIBA BLB PC configuration."""
    return PCConfig(
        identifier="horiba_blb",
        active_device_plugins=("psa_horiba", "dsv_horiba"),
    )
