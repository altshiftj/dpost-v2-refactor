"""Configuration builder for the Zwick UTM tensile testing device."""

from __future__ import annotations

import re

from ipat_watchdog.core.config import (
    DeviceConfig,
    DeviceFileSelectors,
    DeviceMetadata,
    SessionSettings,
    WatcherSettings,
)
from ipat_watchdog.core.config.schema import BatchSettings


def build_config() -> DeviceConfig:
    """Return the Zwick UTM device configuration."""
    return DeviceConfig(
        identifier="utm_zwick",
        metadata=DeviceMetadata(
            user_kadi_id="utm-01-usr",
            user_persistent_id=30,
            record_kadi_id="utm_01",
            record_persistent_id=561,
            device_abbr="UTM",
            record_tags=("Mechanical Test",),
            default_record_description=r"""
## Zwick/Roell Universal Testing Machine

This record contains both the **raw binary output** (`*.zs2`, compressed into ZIP)
and the **post-processed Excel workbook** (`*.xlsx`) for each tensile/compression
test.  Raw files preserve the full resolution of force-displacement channels and
can be re-analysed in Zwick testXpert.  The Excel file includes the calculated
stress-strain curve and summary statistics.

**Typical columns in the workbook**

| Column            | Meaning                       |
|-------------------|-------------------------------|
| Time [s]          | Time stamp since test start   |
| Force [N]         | Load cell reading             |
| Extension [mm]    | Crosshead displacement        |
| Stress [MPa]      | Calculated                    |
| Strain [%]        | Calculated                    |

Please add sample geometry, material batch, gauge length and other context
information below.
""",
        ),
        files=DeviceFileSelectors(
            native_extensions=(".zs2",),
            # Legacy exported .xlsx kept for backward compatibility tests.
            # New workflow will add .csv + multiple .txt snapshots; those are
            # handled dynamically in the processor and do not need explicit
            # enumeration here unless downstream needs probing.
            exported_extensions=(".xlsx", ".csv", ".txt"),
        ),
        session=SessionSettings(timeout_seconds=4 * 3600),
        watcher=WatcherSettings(
            poll_seconds=0.5,
            max_wait_seconds=30,
            stable_cycles=2,
            temp_patterns=(".tmp", ".part", ".crdownload", ".~", "-journal"),
            temp_folder_regex=re.compile(r"\\.[A-Za-z0-9]{6}$"),
            sentinel_name=None,
        ),
        batch=BatchSettings(
            ttl_seconds=0.5 * 3600,  # 30 minutes
            max_batch_size=50,
        ),
        # Extra dynamic attributes consumed by the processor (not part of the
        # core schema strictly, but DeviceConfig is a pydantic model that will
        # retain them). If schema forbids extras this will be refactored to a
        # dedicated plugin settings object.
        extra={
            "series_timeout_minutes": 30,
            "csv_finalize_delay_seconds": 3,
            "flush_incomplete_on_session_end": True,
            "keep_all_intermediate_txt": True,
        },
    )
