"""PC configuration for the BLB tensile testing workstation."""

from __future__ import annotations


from ipat_watchdog.core.config import PCConfig


def build_config() -> PCConfig:
    """Return the Eirich BLB PC configuration."""
    return PCConfig(
        identifier="eirich_blb",
        active_device_plugins=("rmx_eirich_el1", "rmx_eirich_r01"),
    )
