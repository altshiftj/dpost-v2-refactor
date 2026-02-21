"""Configuration builder for the dpost UTM Zwick device plugin."""

from __future__ import annotations

import re

from dpost.application.config import (
    DeviceConfig,
    DeviceFileSelectors,
    DeviceMetadata,
    SessionSettings,
    WatcherSettings,
)
from dpost.application.config.schema import BatchSettings


def build_config() -> DeviceConfig:
    """Return UTM Zwick configuration used by canonical dpost plugin loading."""
    return DeviceConfig(
        identifier="utm_zwick",
        metadata=DeviceMetadata(
            user_kadi_id="utm-01-usr",
            user_persistent_id=30,
            record_kadi_id="utm_01",
            record_persistent_id=561,
            device_abbr="UTM",
            record_tags=("Mechanical Test",),
            default_record_description=(
                "UTM Zwick record containing raw .zs2 artefacts and exported "
                ".xlsx results."
            ),
        ),
        files=DeviceFileSelectors(
            native_extensions=frozenset({".zs2"}),
            exported_extensions=frozenset({".xlsx"}),
        ),
        session=SessionSettings(timeout_seconds=4 * 3600),
        watcher=WatcherSettings(
            poll_seconds=0.5,
            max_wait_seconds=30.0,
            stable_cycles=2,
            temp_patterns=(".tmp", ".part", ".crdownload", ".~", "-journal"),
            temp_folder_regex=re.compile(r"\.[A-Za-z0-9]{6}$"),
            sentinel_name=None,
        ),
        batch=BatchSettings(
            ttl_seconds=int(0.5 * 3600),
            max_batch_size=50,
            flush_on_session_end=True,
        ),
    )
