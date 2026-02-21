"""Tests for DeviceConfig matching behaviour."""
from dataclasses import replace

import pytest

from dpost.application.config import (
    DeviceConfig,
    DeviceFileSelectors,
    SessionSettings,
    WatcherSettings,
)


@pytest.fixture
def base_device_config() -> DeviceConfig:
    return DeviceConfig(
        identifier="device",
        files=DeviceFileSelectors(allowed_extensions={".tiff", ".tif"}),
        session=SessionSettings(timeout_seconds=120),
        watcher=WatcherSettings(poll_seconds=0.1, stable_cycles=2, max_wait_seconds=5.0),
    )


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("sample.tiff", True),
        ("sample.TIF", True),
        ("sample.jpeg", False),
        ("sample.tif.backup", False),
        ("folder/sample.tif", True),
    ],
)
def test_matches_file_by_extension(base_device_config: DeviceConfig, filename: str, expected: bool) -> None:
    assert base_device_config.matches_file(filename) is expected


@pytest.fixture
def directory_matching_config(base_device_config: DeviceConfig) -> DeviceConfig:
    return replace(
        base_device_config,
        files=DeviceFileSelectors(
            allowed_extensions=set(),
            allowed_folder_contents={".dat"},
        ),
    )


def test_matches_directory_by_contents(tmp_path, directory_matching_config: DeviceConfig) -> None:
    folder = tmp_path / "bundle"
    folder.mkdir()
    (folder / "data.dat").write_text("payload")
    (folder / "ignore.txt").write_text("payload")

    assert directory_matching_config.matches_file(folder)


def test_matches_directory_requires_expected_contents(tmp_path, directory_matching_config: DeviceConfig) -> None:
    folder = tmp_path / "bundle"
    folder.mkdir()
    (folder / "ignore.txt").write_text("payload")

    assert directory_matching_config.matches_file(folder) is False


def test_session_and_watcher_defaults(base_device_config: DeviceConfig) -> None:
    assert base_device_config.session.timeout_seconds == 120
    assert base_device_config.watcher.poll_seconds == 0.1
    assert base_device_config.watcher.stable_cycles == 2


def test_matches_all_extensions_when_unrestricted(base_device_config: DeviceConfig) -> None:
    wildcard = replace(
        base_device_config,
        files=DeviceFileSelectors(allowed_extensions=set()),
    )
    assert wildcard.matches_file("anything.random")
