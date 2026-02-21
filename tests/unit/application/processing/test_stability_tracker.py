from __future__ import annotations

from pathlib import Path

import dpost.application.processing.stability_tracker as stability_tracker_module
from dpost.application.config import DeviceConfig, StabilityOverride, WatcherSettings
from dpost.application.processing.stability_tracker import FileStabilityTracker


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


def test_wait_allows_reappear_within_window_and_then_stabilizes(
    tmp_path: Path, monkeypatch
) -> None:
    """A short reappear window should tolerate temporary disappearance."""

    target = tmp_path / "flaky.txt"
    device = DeviceConfig(
        identifier="dev",
        watcher=WatcherSettings(
            reappear_window_seconds=1.0,
            poll_seconds=0.0,
            stable_cycles=1,
            max_wait_seconds=5.0,
        ),
    )

    def _sleep(*_args):
        if not target.exists():
            target.write_text("payload")

    monkeypatch.setattr(FileStabilityTracker, "_sleep", _sleep)

    outcome = FileStabilityTracker(target, device).wait()

    assert outcome.stable is True
    assert outcome.reason is None


def test_wait_stable_cycles_path_sleeps_until_threshold(tmp_path: Path, monkeypatch) -> None:
    """Stable cycle threshold should require repeated unchanged snapshots."""

    target = tmp_path / "steady.txt"
    target.write_text("payload")
    device = DeviceConfig(
        identifier="dev",
        watcher=WatcherSettings(poll_seconds=0.0, stable_cycles=2, max_wait_seconds=5.0),
    )
    tracker = FileStabilityTracker(target, device)
    monkeypatch.setattr(FileStabilityTracker, "_sleep", lambda *_: None)

    outcome = tracker.wait()

    assert outcome.stable is True


def test_await_sentinel_returns_false_without_device(tmp_path: Path) -> None:
    """Sentinel checks are disabled when no device config is present."""

    folder = tmp_path / "batch"
    folder.mkdir()
    tracker = FileStabilityTracker(folder, None)

    assert tracker._await_sentinel(0.0) is False


def test_await_sentinel_returns_false_when_name_not_configured(tmp_path: Path) -> None:
    """Sentinel waits are skipped when sentinel_name is empty."""

    folder = tmp_path / "batch"
    folder.mkdir()
    device = DeviceConfig(identifier="dev", watcher=WatcherSettings(sentinel_name=None))
    tracker = FileStabilityTracker(folder, device)

    assert tracker._await_sentinel(0.0) is False


def test_wait_continues_until_sentinel_appears(tmp_path: Path, monkeypatch) -> None:
    """`wait()` should loop when sentinel is missing, then finish once it appears."""

    folder = tmp_path / "batch"
    folder.mkdir()
    device = DeviceConfig(
        identifier="dev",
        watcher=WatcherSettings(
            sentinel_name="READY",
            poll_seconds=0.0,
            stable_cycles=1,
            max_wait_seconds=5.0,
        ),
    )
    tracker = FileStabilityTracker(folder, device)

    sentinel = folder / "READY"

    def _sleep(*_args):
        if not sentinel.exists():
            sentinel.write_text("ok")

    monkeypatch.setattr(FileStabilityTracker, "_sleep", _sleep)

    outcome = tracker.wait()

    assert outcome.stable is True


def test_snapshot_directory_aggregates_files_and_ignores_missing_child(
    tmp_path: Path, monkeypatch
) -> None:
    """Directory snapshots should skip vanished files instead of failing."""

    folder = tmp_path / "batch"
    folder.mkdir()
    keep = folder / "keep.txt"
    keep.write_text("abc")
    tracker = FileStabilityTracker(folder, None)

    class _MissingPath:
        def stat(self):
            raise FileNotFoundError

    monkeypatch.setattr(
        tracker, "_iter_files", lambda _directory: iter([keep, _MissingPath()])
    )

    snapshot = tracker._snapshot()

    assert snapshot is not None
    assert snapshot[0] == 1
    assert snapshot[1] == keep.stat().st_size


def test_iter_files_supports_string_temp_pattern_and_skips_directories(
    tmp_path: Path,
) -> None:
    """Temp suffix filtering should handle string config values and nested folders."""

    folder = tmp_path / "batch"
    nested = folder / "nested"
    nested.mkdir(parents=True)
    (folder / "keep.txt").write_text("ok")
    (folder / "skip.TMP").write_text("tmp")
    (nested / "child.log").write_text("nested")

    device = DeviceConfig(
        identifier="dev",
        watcher=WatcherSettings(temp_patterns=".tmp"),
    )
    tracker = FileStabilityTracker(folder, device)

    files = sorted(path.name for path in tracker._iter_files(folder))

    assert "keep.txt" in files
    assert "skip.TMP" not in files
    assert "child.log" in files


def test_resolve_override_returns_none_without_device(tmp_path: Path) -> None:
    """Override resolution should be inert without a device configuration."""

    tracker = FileStabilityTracker(tmp_path / "sample.txt", None)
    assert tracker._resolve_override() is None


def test_resolve_override_returns_none_when_no_override_matches(tmp_path: Path) -> None:
    """When no override pattern matches the path, no override is selected."""

    target = tmp_path / "sample.txt"
    override = StabilityOverride(suffixes=(".csv",), poll_seconds=0.2)
    device = DeviceConfig(
        identifier="dev",
        watcher=WatcherSettings(stability_overrides=(override,)),
    )
    tracker = FileStabilityTracker(target, device)

    assert tracker._resolve_override() is None


def test_default_poll_wait_and_cycles_apply_without_device(tmp_path: Path) -> None:
    """Tracker defaults should apply when there is no device-level watcher config."""

    tracker = FileStabilityTracker(tmp_path / "sample.txt", None)

    assert tracker._poll_seconds() == 1.0
    assert tracker._max_wait_seconds() == 300
    assert tracker._stable_cycles() == 3


def test_stable_cycles_uses_device_watcher_when_no_override(tmp_path: Path) -> None:
    """Device watcher stable_cycles should be used absent a matching override."""

    target = tmp_path / "sample.txt"
    device = DeviceConfig(
        identifier="dev",
        watcher=WatcherSettings(stable_cycles=7),
    )
    tracker = FileStabilityTracker(target, device)

    assert tracker._stable_cycles() == 7


def test_reappear_window_defaults_for_missing_or_invalid_values(tmp_path: Path) -> None:
    """Reappear windows should default to zero when unset or malformed."""

    tracker_without_device = FileStabilityTracker(tmp_path / "sample.txt", None)
    assert tracker_without_device._reappear_window_seconds() == 0.0

    device = DeviceConfig(identifier="dev", watcher=WatcherSettings())
    device.watcher.reappear_window_seconds = "bad"
    tracker_with_invalid = FileStabilityTracker(tmp_path / "sample.txt", device)
    assert tracker_with_invalid._reappear_window_seconds() == 0.0


def test_sleep_only_delegates_to_time_sleep_for_positive_seconds(
    monkeypatch,
) -> None:
    """Zero/negative sleeps should be no-ops to keep polling responsive."""

    calls: list[float] = []

    def _fake_sleep(seconds: float) -> None:
        calls.append(seconds)

    monkeypatch.setattr(stability_tracker_module.time, "sleep", _fake_sleep)

    FileStabilityTracker._sleep(0.0)
    FileStabilityTracker._sleep(-1.0)
    FileStabilityTracker._sleep(0.25)

    assert calls == [0.25]
