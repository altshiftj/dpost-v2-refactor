"""Configuration builder for the dpost EXTR HAAKE device plugin."""

from __future__ import annotations

from dpost.application.config import (
    DeviceConfig,
    DeviceFileSelectors,
    DeviceMetadata,
    SessionSettings,
    WatcherSettings,
)


def build_config() -> DeviceConfig:
    """Return EXTR HAAKE configuration used by canonical dpost loading."""
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
            native_extensions=frozenset({".xlsx"}),
            allowed_extensions=frozenset({".xlsx", ".xls", ".xlsm"}),
        ),
        session=SessionSettings(timeout_seconds=900),
        watcher=WatcherSettings(
            # Excel safe-save can flap the target path, so use a longer window.
            poll_seconds=0.5,
            max_wait_seconds=90.0,
            stable_cycles=3,
            sentinel_name=None,
            reappear_window_seconds=6.0,
        ),
    )
