"""Configuration builder for the dpost DSV HORIBA device plugin."""

from __future__ import annotations

from dpost.application.config import (
    DeviceConfig,
    DeviceFileSelectors,
    DeviceMetadata,
    SessionSettings,
    WatcherSettings,
)


def build_config() -> DeviceConfig:
    """Return the Horiba dissolver device configuration."""
    return DeviceConfig(
        identifier="dsv_horiba",
        metadata=DeviceMetadata(
            user_kadi_id="dsv-01-usr",
            user_persistent_id=31,
            record_kadi_id="dsv_01",
            record_persistent_id=562,
            device_abbr="DSV",
            record_tags=("Dissolution Test", "Particle Analysis"),
            default_record_description=r"""
## Horiba Dissolver Analysis

This record contains both the **raw binary data** (`*.wdb`, `*.wdk`, `*.wdp`, compressed into ZIP)
and the **exported text files** (`*.txt`) from dissolution tests. Raw files preserve the full
measurement data and can be re-analyzed with Horiba software. The text files contain the
processed results and dissolution curves.

**File types:**
- `.wdb` - Raw database file
- `.wdk` - Raw data configuration
- `.wdp` - Raw data parameters
- `.txt` - Exported dissolution results and curves

**Analysis parameters:** Sample size, dissolution medium, temperature, stirring rate.
""",
        ),
        files=DeviceFileSelectors(
            native_extensions=frozenset({".wdb", ".wdk", ".wdp"}),
            exported_extensions=frozenset({".txt"}),
        ),
        session=SessionSettings(timeout_seconds=600),
        watcher=WatcherSettings(),
    )
