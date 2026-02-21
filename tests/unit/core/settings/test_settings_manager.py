"""Unit tests for the configuration service."""
from __future__ import annotations

import threading

import pytest

from dpost.application.config import (
    ConfigService,
    DeviceConfig,
    DeviceFileSelectors,
    DeviceMetadata,
    NamingSettings,
    PathSettings,
    PCConfig,
    SessionSettings,
)


@pytest.fixture
def service(tmp_path) -> ConfigService:
    base = tmp_path / "sandbox"
    paths = PathSettings(
        app_dir=base / "app",
        desktop_dir=base,
        watch_dir=base / "watch",
        dest_dir=base / "dest",
        rename_dir=base / "dest" / "00_To_Rename",
        exceptions_dir=base / "dest" / "01_Exceptions",
        daily_records_json=base / "records.json",
    )

    pc = PCConfig(
        identifier="pc",
        paths=paths,
        naming=NamingSettings(id_separator="-", file_separator="_"),
        session=SessionSettings(timeout_seconds=600),
        active_device_plugins=("device_a", "device_b"),
    )

    device_a = DeviceConfig(
        identifier="device_a",
        metadata=DeviceMetadata(device_abbr="A", default_record_description="A"),
        files=DeviceFileSelectors(native_extensions={".tiff", ".tif"}, exported_extensions={".jpeg"}),
        session=SessionSettings(timeout_seconds=120),
    )
    device_b = DeviceConfig(
        identifier="device_b",
        metadata=DeviceMetadata(device_abbr="B", default_record_description="B"),
        files=DeviceFileSelectors(native_extensions={".txt"}, exported_extensions={".csv"}),
        session=SessionSettings(timeout_seconds=300),
    )

    return ConfigService(pc, [device_a, device_b])


def test_devices_property(service):
    identifiers = {device.identifier for device in service.devices}
    assert identifiers == {"device_a", "device_b"}


def test_first_matching_device(service):
    assert service.first_matching_device("foo.tif").identifier == "device_a"
    assert service.first_matching_device("foo.txt").identifier == "device_b"
    assert service.first_matching_device("foo.bin") is None


def test_activation_scoping(service):
    assert service.current_device() is None

    with service.activate_device("device_a"):
        assert service.current_device().identifier == "device_a"
        with service.activate_device("device_b"):
            assert service.current_device().identifier == "device_b"
        assert service.current_device().identifier == "device_a"

    assert service.current_device() is None


def test_activation_is_thread_local(service):
    results = {}

    def worker(name):
        with service.activate_device(name):
            results[name] = service.current_device().identifier

    threads = [threading.Thread(target=worker, args=(identifier,)) for identifier in ("device_a", "device_b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results == {"device_a": "device_a", "device_b": "device_b"}
    assert service.current_device() is None
