from __future__ import annotations

from pathlib import Path

from ipat_watchdog.core.config.schema import DeviceConfig, StabilityOverride, WatcherSettings
from ipat_watchdog.core.processing.stability_tracker import FileStabilityTracker


def test_wait_rejects_disappeared_path(tmp_path: Path):
    missing = tmp_path / "missing.txt"
    device = DeviceConfig(identifier="dev", watcher=WatcherSettings(reappear_window_seconds=0.0))

    outcome = FileStabilityTracker(missing, device).wait()

    assert outcome.rejected is True
    assert "disappeared" in (outcome.reason or "")


def test_wait_times_out_when_max_wait_zero(tmp_path: Path, monkeypatch):
    target = tmp_path / "file.txt"
    target.write_text("data")
    device = DeviceConfig(
        identifier="dev",
        watcher=WatcherSettings(max_wait_seconds=0.0, poll_seconds=0.0, stable_cycles=1),
    )

    monkeypatch.setattr(FileStabilityTracker, "_sleep", lambda *_: None)

    outcome = FileStabilityTracker(target, device).wait()

    assert outcome.rejected is True
    assert "Timeout" in (outcome.reason or "")


def test_await_sentinel_blocks_until_present(tmp_path: Path, monkeypatch):
    folder = tmp_path / "batch"
    folder.mkdir()
    device = DeviceConfig(
        identifier="dev",
        watcher=WatcherSettings(sentinel_name="READY", poll_seconds=0.0),
    )
    tracker = FileStabilityTracker(folder, device)

    monkeypatch.setattr(FileStabilityTracker, "_sleep", lambda *_: None)

    assert tracker._await_sentinel(0.0) is True

    sentinel = folder / "READY"
    sentinel.write_text("ok")
    assert tracker._await_sentinel(0.0) is False


def test_iter_files_excludes_temp_patterns(tmp_path: Path):
    folder = tmp_path / "batch"
    folder.mkdir()
    (folder / "keep.txt").write_text("ok")
    (folder / "skip.tmp").write_text("temp")

    device = DeviceConfig(
        identifier="dev",
        watcher=WatcherSettings(temp_patterns=(".tmp",)),
    )
    tracker = FileStabilityTracker(folder, device)

    files = [path.name for path in tracker._iter_files(folder)]

    assert "keep.txt" in files
    assert "skip.tmp" not in files


def test_override_controls_poll_and_cycles(tmp_path: Path):
    target = tmp_path / "sample.dat"
    target.write_text("data")

    override = StabilityOverride(
        suffixes=(".dat",),
        poll_seconds=0.1,
        stable_cycles=1,
        max_wait_seconds=2,
    )
    device = DeviceConfig(
        identifier="dev",
        watcher=WatcherSettings(
            poll_seconds=5.0,
            stable_cycles=3,
            max_wait_seconds=10.0,
            stability_overrides=(override,),
        ),
    )

    tracker = FileStabilityTracker(target, device)

    assert tracker._poll_seconds() == 0.1
    assert tracker._stable_cycles() == 1
    assert tracker._max_wait_seconds() == 2
