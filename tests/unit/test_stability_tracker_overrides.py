from pathlib import Path

import pytest

from ipat_watchdog.core.config import (
    DeviceConfig,
    DeviceFileSelectors,
    DeviceMetadata,
    SessionSettings,
    StabilityOverride,
    WatcherSettings,
)
from ipat_watchdog.core.processing.stability_tracker import FileStabilityTracker


def _build_config(*overrides: StabilityOverride) -> DeviceConfig:
    return DeviceConfig(
        identifier="override-test",
        metadata=DeviceMetadata(),
        files=DeviceFileSelectors(allowed_extensions={".tiff", ".elid"}),
        session=SessionSettings(timeout_seconds=10),
        watcher=WatcherSettings(
            poll_seconds=0.5,
            max_wait_seconds=45,
            stable_cycles=4,
            stability_overrides=overrides,
        ),
    )


def test_tracker_applies_suffix_override(tmp_path: Path) -> None:
    file_path = tmp_path / "image.tiff"
    file_path.write_bytes(b"test")

    override = StabilityOverride(
        suffixes=(".tiff",),
        poll_seconds=0.1,
        stable_cycles=1,
        max_wait_seconds=12,
    )
    tracker = FileStabilityTracker(file_path, _build_config(override))

    assert pytest.approx(tracker._poll_seconds()) == 0.1
    assert tracker._stable_cycles() == 1
    assert tracker._max_wait_seconds() == 12


def test_tracker_applies_directory_override(tmp_path: Path) -> None:
    dir_path = tmp_path / "elid"
    dir_path.mkdir()

    override = StabilityOverride(
        folders=("elid",),
        stable_cycles=7,
        poll_seconds=0.75,
    )
    tracker = FileStabilityTracker(dir_path, _build_config(override))

    assert pytest.approx(tracker._poll_seconds()) == 0.75
    assert tracker._stable_cycles() == 7
    # Falls back to watcher default when override omits a value
    assert tracker._max_wait_seconds() == 45
