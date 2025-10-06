"""Configuration factory for the ETR twin-screw extruder device plugin."""

from __future__ import annotations

from ipat_watchdog.core.config import (
    DeviceConfig,
    DeviceFileSelectors,
    DeviceMetadata,
    SessionSettings,
    WatcherSettings,
)


def build_config() -> DeviceConfig:
    """Return the standard configuration for the ETR twin-screw extruder."""

    return DeviceConfig(
        identifier="etr_twinscrew",
        metadata=DeviceMetadata(
            user_kadi_id="etr-01-user",
            user_persistent_id=-1,
            record_kadi_id="etr_01",
            record_persistent_id=-1,
            device_abbr="ETR",
            record_tags=("Extrusion", "Twin Screw"),
            default_record_description=(
                "Twin-screw extrusion dataset captured from the ETR workstation and saved as Excel output."
            ),
        ),
        files=DeviceFileSelectors(
            native_extensions={".xlsx"},
            allowed_extensions={".xlsx", ".xls", ".xlsm"},
        ),
        session=SessionSettings(timeout_seconds=900),
        watcher=WatcherSettings(
            poll_seconds=1.0,
            max_wait_seconds=45.0,
            stable_cycles=2,
            sentinel_name=None,
        ),
    )
