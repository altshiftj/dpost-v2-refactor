"""Tests for ActiveConfig behaviour."""
from pathlib import Path

from ipat_watchdog.core.config.service import ActiveConfig
from ipat_watchdog.core.config.schema import (
    DeviceConfig,
    DeviceFileSelectors,
    DeviceMetadata,
    NamingSettings,
    PathSettings,
    PCConfig,
    SessionSettings,
    WatcherSettings,
)


def _pc_config(tmp_path):
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
    return PCConfig(
        identifier="pc",
        paths=paths,
        naming=NamingSettings(id_separator="-", file_separator="_"),
        session=SessionSettings(timeout_seconds=600),
        watcher=WatcherSettings(poll_seconds=0.5, max_wait_seconds=10.0, stable_cycles=3),
    )


def _device_config():
    return DeviceConfig(
        identifier="device",
        metadata=DeviceMetadata(device_abbr="DEV", default_record_description="desc"),
        files=DeviceFileSelectors(allowed_extensions={".tif"}),
        session=SessionSettings(timeout_seconds=120),
        watcher=WatcherSettings(poll_seconds=0.1, max_wait_seconds=5.0, stable_cycles=1),
    )


def test_active_config_pc_only(tmp_path):
    pc = _pc_config(tmp_path)
    active = ActiveConfig(pc=pc, device=None)

    assert active.device is None
    assert active.session_timeout == pc.session.timeout_seconds
    assert active.paths.dest_dir == pc.paths.dest_dir
    assert active.id_separator == pc.naming.id_separator


def test_active_config_device_overrides(tmp_path):
    pc = _pc_config(tmp_path)
    device = _device_config()

    active = ActiveConfig(pc=pc, device=device)

    assert active.device.identifier == "device"
    assert active.session_timeout == device.session.timeout_seconds
    assert active.watcher.poll_seconds == device.watcher.poll_seconds
    assert active.device_metadata.device_abbr == "DEV"


def test_active_config_directory_list(tmp_path):
    pc = _pc_config(tmp_path)
    active = ActiveConfig(pc=pc, device=None)
    dirs = active.directory_list
    assert pc.paths.watch_dir in dirs
