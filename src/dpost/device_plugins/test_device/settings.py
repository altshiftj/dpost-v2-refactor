"""Configuration scaffold for the dpost reference test device plugin."""

from __future__ import annotations

import re

from dpost.application.config import (
    DeviceConfig,
    DeviceFileSelectors,
    DeviceMetadata,
    SessionSettings,
    WatcherSettings,
)


def build_config() -> DeviceConfig:
    """Return the standardised configuration used by dpost test-device plugin."""
    return DeviceConfig(
        identifier="test_device",
        metadata=DeviceMetadata(
            user_kadi_id="test-01-usr",
            user_persistent_id=999,
            record_kadi_id="test_01",
            record_persistent_id=999,
            device_abbr="TEST",
            record_tags=("Test Data", "Unit Testing"),
            default_record_description=(
                "Reference test record used for migration and runtime validation."
            ),
        ),
        files=DeviceFileSelectors(
            allowed_extensions=frozenset({".tif", ".txt"}),
            native_extensions=frozenset({".tif"}),
        ),
        session=SessionSettings(timeout_seconds=300),
        watcher=WatcherSettings(
            poll_seconds=0.25,
            max_wait_seconds=3.0,
            stable_cycles=2,
            temp_patterns=(".tmp", ".part", ".crdownload", ".~", "-journal"),
            temp_folder_regex=re.compile(r"\.[A-Za-z0-9]{6}$"),
            sentinel_name=None,
        ),
    )
