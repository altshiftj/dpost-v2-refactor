"""PC-level configuration for the Horiba BLB acquisition workstation."""

from __future__ import annotations

import re

from ipat_watchdog.core.config import PCConfig


def build_config() -> PCConfig:
    """Return the Horiba BLB PC configuration."""
    return PCConfig(
        identifier="horiba_blb",
        active_device_plugins=("psa_horiba", "dsv_horiba"),
    )
