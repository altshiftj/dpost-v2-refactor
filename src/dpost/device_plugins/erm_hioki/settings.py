"""Configuration builder for the dpost ERM HIOKI device plugin."""

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
    """Return the HIOKI device configuration."""
    return DeviceConfig(
        identifier="erm_hioki",
        metadata=DeviceMetadata(
            user_kadi_id="erm-01-user",
            user_persistent_id=53,
            record_kadi_id="erm_01",
            record_persistent_id=913,
            device_abbr="ERM",
            record_tags=("Electrode Resistance Measurement",),
            default_record_description=(
                "**Overview**\n\n"
                "This record contains data exported from a Hioki instrument. "
                "Exports are typically Excel workbooks (.xlsx/.xls) and may also "
                "include .csv files.\n\n"
                "**Data Types**\n\n"
                "Exported files are appended into the record folder using unique, "
                "collision-safe names. No native bundling is required for Hioki in "
                "this configuration."
            ),
        ),
        files=DeviceFileSelectors(
            native_extensions=frozenset(),
            exported_extensions=frozenset({".xlsx", ".xls", ".csv"}),
        ),
        session=SessionSettings(timeout_seconds=600),
        watcher=WatcherSettings(
            poll_seconds=1.0,
            max_wait_seconds=30,
            stable_cycles=2,
            temp_patterns=(".tmp", ".part", ".crdownload", "~", ".journal"),
            temp_folder_regex=re.compile(r"(\.~|\.staged|__staged__)"),
            sentinel_name=None,
        ),
    )
