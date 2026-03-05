"""PC configuration for the Mischraum extruder workstation."""

from __future__ import annotations

from ipat_watchdog.core.config import PCConfig


def build_config() -> PCConfig:
    """Return the Mischraum extruder PC configuration."""
    return PCConfig(
        identifier="haake_blb",
        active_device_plugins=("extr_haake",),
    )
