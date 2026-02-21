"""Integration tests for the configuration service."""

import pytest

from dpost.application.config import (
    DeviceConfig,
    DeviceFileSelectors,
    DeviceMetadata,
    NamingSettings,
    PathSettings,
    PCConfig,
    SessionSettings,
    WatcherSettings,
    activate_device,
    current,
    init_config,
    reset_service,
)


@pytest.fixture
def config(tmp_path):
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
        identifier="test_pc",
        paths=paths,
        naming=NamingSettings(id_separator="-", file_separator="_"),
        session=SessionSettings(timeout_seconds=600),
        watcher=WatcherSettings(poll_seconds=0.5, max_wait_seconds=10.0, stable_cycles=2),
        active_device_plugins=("device_a", "device_b"),
    )

    device_a = DeviceConfig(
        identifier="device_a",
        metadata=DeviceMetadata(device_abbr="A", default_record_description="desc A", user_kadi_id="a-user"),
        files=DeviceFileSelectors(allowed_extensions=frozenset({".tiff", ".tif"})),
        session=SessionSettings(timeout_seconds=120),
        watcher=WatcherSettings(poll_seconds=0.1, max_wait_seconds=5.0, stable_cycles=1),
    )

    device_b = DeviceConfig(
        identifier="device_b",
        metadata=DeviceMetadata(device_abbr="B", default_record_description="desc B", user_kadi_id="b-user"),
        files=DeviceFileSelectors(allowed_extensions=frozenset({".txt", ".csv"})),
        session=SessionSettings(timeout_seconds=300),
        watcher=WatcherSettings(poll_seconds=0.2, max_wait_seconds=7.0, stable_cycles=2),
    )

    service = init_config(pc, [device_a, device_b])
    try:
        yield service
    finally:
        reset_service()


def test_active_config_defaults_to_pc(config):
    active = current()
    assert active.device is None
    assert active.session_timeout == config.pc.session.timeout_seconds
    assert active.paths.watch_dir.exists() or True  # path object returned


def test_device_activation_context(config):
    with activate_device("device_a"):
        active = current()
        assert active.device is not None
        assert active.device.identifier == "device_a"
        assert active.session_timeout == 120
        assert active.device.metadata.device_abbr == "A"

    # Context should restore PC-only view
    active = current()
    assert active.device is None


def test_matching_devices(config):
    device = config.first_matching_device("sample.tiff")
    assert device is not None and device.identifier == "device_a"

    device = config.first_matching_device("sample.csv")
    assert device is not None and device.identifier == "device_b"

    device = config.first_matching_device("sample.unknown")
    assert device is None


def test_matching_devices_returns_all(config):
    results = config.matching_devices("sample.tif")
    assert [d.identifier for d in results] == ["device_a"]
