"""Configuration factory for Hioki analyzer exports (Excel/CSV)."""
from __future__ import annotations

from ipat_watchdog.core.config import (
    DeviceConfig,
    DeviceFileSelectors,
    DeviceMetadata,
    SessionSettings,
    WatcherSettings,
)

def build_config() -> DeviceConfig:
    """Return the Hioki device configuration."""
    return DeviceConfig(
        identifier="hioki_blb",
        metadata=DeviceMetadata(
            user_kadi_id="<tbd>",
            record_kadi_id="<tbd>",
            device_abbr="HIO",
            record_tags=("Hioki", "Electrical", "LabExport"),
            default_record_description=(
                "**Overview**\n\n"
                "This record contains data exported from a Hioki instrument. "
                "Exports are typically Excel workbooks (.xlsx/.xls) and may also include .csv files.\n\n"
                "**Data Types**\n\n"
                "Exported files are appended into the record folder using unique, collision-safe names. "
                "No native bundling is required for Hioki in this configuration."
            ),
        ),
        files=DeviceFileSelectors(
            native_extensions=(),                         # no native format handled here
            exported_extensions=(".xlsx", ".xls", ".csv") # Excel + CSV
        ),
        session=SessionSettings(
            timeout_seconds=600,
        ),
        watcher=WatcherSettings(
            poll_seconds=1.0,
            max_wait_seconds=30,
            stable_cycles=2,
            temp_patterns=(".tmp", ".part", ".crdownload", "~", ".journal"),
            temp_folder_regex=r"(\.~|\.staged|__staged__)",
            sentinel_name=None,
        ),
    )
