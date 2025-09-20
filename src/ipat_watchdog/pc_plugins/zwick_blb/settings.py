"""PC configuration for the BLB tensile testing workstation."""

from __future__ import annotations

import re

from ipat_watchdog.core.config import PCConfig, SessionSettings, WatcherSettings


def build_config() -> PCConfig:
    """Return the Zwick BLB PC configuration."""
    return PCConfig(
        identifier="zwick_blb",
        session=SessionSettings(timeout_seconds=600),
        watcher=WatcherSettings(
            poll_seconds=1.5,
            max_wait_seconds=30.0,
            stable_cycles=3,
            temp_folder_regex=re.compile(r"\\.[A-Za-z0-9]{6}$"),
        ),
        active_device_plugins=("utm_zwick",),
    )
