#!/usr/bin/env python3
"""
Manual smoke test demonstrating config service wiring with the sync manager.
"""
import pytest

pytest.importorskip("kadi_apy")
from pathlib import Path

from dpost.application.config import (
    DeviceConfig,
    DeviceFileSelectors,
    DeviceMetadata,
    PathSettings,
    PCConfig,
    SessionSettings,
    init_config,
    reset_service,
)
from dpost.infrastructure.sync.kadi_manager import KadiSyncManager
from tests.helpers.fake_ui import HeadlessUI


def test_sync_settings_integration(tmp_path):
    base = tmp_path / "sandbox"
    paths = PathSettings(
        app_dir=base / "App",
        desktop_dir=base,
        watch_dir=base / "Upload",
        dest_dir=base / "Data",
        rename_dir=base / "Data" / "00_To_Rename",
        exceptions_dir=base / "Data" / "01_Exceptions",
        daily_records_json=base / "records.json",
    )

    pc = PCConfig(
        identifier="manual_pc",
        paths=paths,
        session=SessionSettings(timeout_seconds=600),
        active_device_plugins=("manual_device",),
    )

    device = DeviceConfig(
        identifier="manual_device",
        metadata=DeviceMetadata(device_abbr="MANUAL", default_record_description="Manual test device"),
        files=DeviceFileSelectors(allowed_extensions=frozenset({".tif"})),
        session=SessionSettings(timeout_seconds=120),
    )

    init_config(pc, [device])
    try:
        ui = HeadlessUI()
        sync_manager = KadiSyncManager(interactions=ui)
        assert sync_manager is not None
    finally:
        reset_service()


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_sync_settings_integration(Path(tmp))
        print("Manual sync integration smoke test completed.")
