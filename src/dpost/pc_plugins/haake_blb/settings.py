"""PC configuration for the dpost HAAKE BLB workstation plugin."""

from __future__ import annotations

from dpost.application.config import PCConfig


def build_config() -> PCConfig:
    """Return the HAAKE BLB PC configuration."""
    return PCConfig(
        identifier="haake_blb",
        active_device_plugins=("extr_haake",),
    )
