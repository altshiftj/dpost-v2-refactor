"""Tests for ActiveConfig behaviour."""
from dataclasses import replace

import pytest

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


@pytest.fixture
def pc_config(tmp_path) -> PCConfig:
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
        active_device_plugins=("device",),
    )


@pytest.fixture
def device_config() -> DeviceConfig:
    return DeviceConfig(
        identifier="device",
        metadata=DeviceMetadata(device_abbr="DEV", default_record_description="desc"),
        files=DeviceFileSelectors(allowed_extensions={".tif"}),
        session=SessionSettings(timeout_seconds=120),
        watcher=WatcherSettings(poll_seconds=0.1, max_wait_seconds=5.0, stable_cycles=1),
    )


def test_active_config_pc_only(pc_config: PCConfig) -> None:
    active = ActiveConfig(pc=pc_config, device=None)

    assert active.device is None
    assert active.session_timeout == pc_config.session.timeout_seconds
    assert active.paths.dest_dir == pc_config.paths.dest_dir
    assert active.id_separator == pc_config.naming.id_separator
    assert active.file_separator == pc_config.naming.file_separator


def test_active_config_device_overrides(pc_config: PCConfig, device_config: DeviceConfig) -> None:
    active = ActiveConfig(pc=pc_config, device=device_config)

    assert active.device.identifier == "device"
    assert active.session_timeout == device_config.session.timeout_seconds
    assert active.watcher.poll_seconds == device_config.watcher.poll_seconds
    assert active.device_metadata.device_abbr == "DEV"


def test_directory_list_contains_key_paths(pc_config: PCConfig) -> None:
    active = ActiveConfig(pc=pc_config, device=None)
    directory_list = active.directory_list

    expected = {
        pc_config.paths.watch_dir,
        pc_config.paths.dest_dir,
        pc_config.paths.rename_dir,
        pc_config.paths.exceptions_dir,
    }
    assert expected.issubset(set(directory_list))


@pytest.mark.parametrize(
    ("device_timeout", "expected"),
    [
        (90, 90),
        (-1, 600),
    ],
)
def test_session_timeout_prefers_device_when_valid(
    pc_config: PCConfig,
    device_config: DeviceConfig,
    device_timeout: int,
    expected: int,
) -> None:
    device = replace(
        device_config,
        session=replace(device_config.session, timeout_seconds=device_timeout),
    )

    active = ActiveConfig(pc=pc_config, device=device)
    assert active.session_timeout == expected


def test_watcher_defaults_to_pc_when_device_missing(pc_config: PCConfig) -> None:
    active = ActiveConfig(pc=pc_config, device=None)
    assert active.watcher is pc_config.watcher
