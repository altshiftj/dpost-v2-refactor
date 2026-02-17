
from __future__ import annotations


from ipat_watchdog.core.config import PCConfig


def build_config() -> PCConfig:
    """Return the Hioki BLB PC configuration."""
    return PCConfig(
        identifier="hioki_blb",
        active_device_plugins=("erm_hioki",),
    )