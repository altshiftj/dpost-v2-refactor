"""PC configuration for the BLB tensile testing workstation."""

from __future__ import annotations

import re

from ipat_watchdog.core.config import PCConfig, SessionSettings, WatcherSettings


def build_config() -> PCConfig:
    """Return the Zwick BLB PC configuration."""
    return PCConfig(
        identifier="zwick_blb",
        active_device_plugins=("utm_zwick",),
    )
