"""Configuration factory for the Thermofisher HAAKE extruder device plugin."""

from __future__ import annotations

from ipat_watchdog.core.config import (
    DeviceConfig,
    DeviceFileSelectors,
    DeviceMetadata,
    SessionSettings,
    WatcherSettings,
)


def build_config() -> DeviceConfig:
    """Return the standard configuration for the Thermofisher HAAKE extruder."""

    return DeviceConfig(
        identifier="extr_haake",
        metadata=DeviceMetadata(
            user_kadi_id="extr-01-user",
            user_persistent_id=40,
            record_kadi_id="extr_01",
            record_persistent_id=745,
            device_abbr="EXTR",
            record_tags=("Extrusion",),
            default_record_description=(
                "Dataset captured from the Thermofisher HAAKE Extruder."
            ),
        ),
        files=DeviceFileSelectors(
            native_extensions={".xlsx"},
            allowed_extensions={".xlsx", ".xls", ".xlsm"},
        ),
        session=SessionSettings(timeout_seconds=900),
        watcher=WatcherSettings(
            # Excel safe-save can flap the target path; be a bit more patient here.
            poll_seconds=0.5,
            max_wait_seconds=90.0,
            stable_cycles=3,
            sentinel_name=None,
            reappear_window_seconds=6.0,
        ),
    )
