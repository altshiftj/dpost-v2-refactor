"""Configuration scaffold for the synthetic test device plugin."""

from __future__ import annotations

import re

from ipat_watchdog.core.config import (
    DeviceConfig,
    DeviceFileSelectors,
    DeviceMetadata,
    SessionSettings,
    WatcherSettings,
)


def build_config() -> DeviceConfig:
    """Return the standardised configuration used by test device plugins."""
    return DeviceConfig(
        identifier="test_device",
        metadata=DeviceMetadata(
            user_kadi_id="test-01-usr",
            user_persistent_id=999,
            record_kadi_id="test_01",
            record_persistent_id=999,
            device_abbr="TEST",
            record_tags=("Test Data", "Unit Testing"),
            default_record_description=r"""
    # Test Record Description
    *This is a test record created during automated testing*

    ## Overview
    **Device:** Test Device for Unit/Integration Testing
    **Data Types:** Test files (.tif, .txt)
    
    This record was created by the test suite and contains synthetic test data.
    """,
        ),
            files=DeviceFileSelectors(
                allowed_extensions={".tif", ".txt"},
                native_extensions={".tif"},
            ),
        session=SessionSettings(timeout_seconds=300),
        watcher=WatcherSettings(
            poll_seconds=0.25,
            max_wait_seconds=3,
            stable_cycles=2,
            temp_patterns=(".tmp", ".part", ".crdownload", ".~", "-journal"),
            temp_folder_regex=re.compile(r"\\.[A-Za-z0-9]{6}$"),
            sentinel_name=None,
        ),
    )
