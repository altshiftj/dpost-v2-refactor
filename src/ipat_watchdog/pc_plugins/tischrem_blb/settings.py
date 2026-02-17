"""PC configuration for the TischREM BLB microscope workstation."""

from __future__ import annotations


from ipat_watchdog.core.config import PCConfig


def build_config() -> PCConfig:
    """Return the TischREM BLB PC configuration."""
    return PCConfig(
        identifier="tischrem_blb",
        active_device_plugins=("sem_phenomxl2",),
    )
