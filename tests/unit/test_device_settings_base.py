"""Tests for DeviceConfig matching behaviour."""
from pathlib import Path

from ipat_watchdog.core.config.schema import DeviceConfig, DeviceFileSelectors, SessionSettings, WatcherSettings


def test_matches_file_by_extension():
    config = DeviceConfig(
        identifier="device",
        files=DeviceFileSelectors(allowed_extensions={".tiff", ".tif"}),
    )

    assert config.matches_file("sample.tiff")
    assert config.matches_file("sample.TIF")
    assert not config.matches_file("sample.txt")


def test_matches_directory_by_contents(tmp_path):
    config = DeviceConfig(
        identifier="device",
        files=DeviceFileSelectors(allowed_extensions=set(), allowed_folder_contents={".dat"}),
    )

    folder = tmp_path / "bundle"
    folder.mkdir()
    (folder / "data.dat").write_text("payload")
    (folder / "ignore.txt").write_text("payload")

    assert config.matches_file(str(folder))


def test_session_and_watcher_defaults():
    config = DeviceConfig(
        identifier="device",
        session=SessionSettings(timeout_seconds=120),
        watcher=WatcherSettings(poll_seconds=0.1, stable_cycles=2, max_wait_seconds=5.0),
    )

    assert config.session.timeout_seconds == 120
    assert config.watcher.poll_seconds == 0.1
    assert config.watcher.stable_cycles == 2
