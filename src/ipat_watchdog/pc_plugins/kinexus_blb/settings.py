from __future__ import annotations

import re

from ipat_watchdog.core.config import PCConfig


def build_config() -> PCConfig:
    """Return the Horiba BLB PC configuration."""
    return PCConfig(
        identifier="kinexus_blb",
        active_device_plugins=("rhe_kinexus",),
    )
