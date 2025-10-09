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
        session=SessionSettings(
            timeout_seconds=900
        ),
        watcher=WatcherSettings(
            poll_seconds=1.0,
            max_wait_seconds=45.0,
            stable_cycles=2,
            sentinel_name=None,
        ),
    )
