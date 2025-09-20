"""PC-level configuration for the Horiba BLB acquisition workstation."""

from __future__ import annotations

import re

from ipat_watchdog.core.config import (
    NamingSettings,
    PCConfig,
    SessionSettings,
    WatcherSettings,
)


def build_config() -> PCConfig:
    """Return the Horiba BLB PC configuration."""
    return PCConfig(
        identifier="horiba_blb",
        session=SessionSettings(timeout_seconds=600),
        watcher=WatcherSettings(
            poll_seconds=1.5,
            max_wait_seconds=30.0,
            stable_cycles=3,
            temp_folder_regex=re.compile(r"\\.[A-Za-z0-9]{6}$"),
        ),
        active_device_plugins=("psa_horiba", "dsv_horiba"),
        naming=NamingSettings(),
    )
