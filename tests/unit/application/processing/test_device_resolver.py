from __future__ import annotations

import logging
from pathlib import Path

import pytest

from dpost.application.config import DeviceConfig, WatcherSettings
from dpost.application.processing.device_resolver import (
    DeviceResolution,
    DeviceResolutionKind,
    DeviceResolver,
    ProbeAssessment,
)
from dpost.application.processing.file_processor_abstract import FileProbeResult


class DummyConfigService:
    def __init__(self, matching=None, deferred=None):
        self._matching = matching or []
        self._deferred = deferred or []

    def matching_devices(self, path_like):
        return list(self._matching)

    def deferred_devices(self, path_like):
        return list(self._deferred)


class DummyProcessor:
    def __init__(self, result):
        self._result = result

    def probe_file(self, filepath):
        return self._result


class DummyFactory:
    def __init__(self, results_by_id):
        self._results_by_id = results_by_id

    def get_for_device(self, device_id):
        return DummyProcessor(self._results_by_id[device_id])


def _device(identifier: str, *, reappear: float = 0.0, retry_delay: float = 2.0) -> DeviceConfig:
    watcher = WatcherSettings(reappear_window_seconds=reappear, retry_delay_seconds=retry_delay)
    return DeviceConfig(identifier=identifier, watcher=watcher)


def _assessment(
    device: DeviceConfig,
    result: FileProbeResult,
    processor_name: str = "DummyProcessor",
) -> ProbeAssessment:
    """Build a probe assessment for chooser/reason helper tests."""

    return ProbeAssessment(device=device, result=result, processor_name=processor_name)


def test_resolve_missing_path_selects_reappear_device(tmp_path: Path):
    target = tmp_path / "missing.txt"
    device = _device("dev1", reappear=1.0)
    resolver = DeviceResolver(DummyConfigService(matching=[device]), DummyFactory({}))

    resolution = resolver.resolve(target)

    assert resolution.selected == device
    assert resolution.kind is DeviceResolutionKind.ACCEPT
    assert resolution.deferred is False
    assert resolution.retry_delay is None
    assert "waiting for reappearance" in resolution.reason


def test_resolve_missing_path_defers_without_reappear(tmp_path: Path):
    target = tmp_path / "missing.txt"
    device = _device("dev1", reappear=0.0)
    resolver = DeviceResolver(DummyConfigService(matching=[device]), DummyFactory({}))

    resolution = resolver.resolve(target)

    assert resolution.selected is None
    assert resolution.kind is DeviceResolutionKind.DEFER
    assert resolution.deferred is True
    assert "disappeared" in resolution.reason


def test_resolve_defers_for_deferred_devices(tmp_path: Path):
    target = tmp_path / "file.txt"
    target.write_text("data")
    device = _device("dev1", retry_delay=4.5)
    resolver = DeviceResolver(DummyConfigService(matching=[], deferred=[device]), DummyFactory({}))

    resolution = resolver.resolve(target)

    assert resolution.kind is DeviceResolutionKind.DEFER
    assert resolution.deferred is True
    assert resolution.retry_delay == 4.5
    assert "dev1" in resolution.reason


def test_resolve_defers_for_empty_directory(tmp_path: Path):
    target = tmp_path / "empty"
    target.mkdir()
    resolver = DeviceResolver(DummyConfigService(matching=[], deferred=[]), DummyFactory({}))

    resolution = resolver.resolve(target)

    assert resolution.kind is DeviceResolutionKind.DEFER
    assert resolution.deferred is True
    assert "Deferred until" in resolution.reason


def test_resolve_with_no_candidates_for_file_reports_unmatched_reason(
    tmp_path: Path,
) -> None:
    """Regular files without selector hits should fail fast without deferral."""

    target = tmp_path / "file.txt"
    target.write_text("data")
    resolver = DeviceResolver(DummyConfigService(matching=[], deferred=[]), DummyFactory({}))

    resolution = resolver.resolve(target)

    assert resolution.selected is None
    assert resolution.kind is DeviceResolutionKind.REJECT
    assert resolution.deferred is False
    assert resolution.reason == "No device selectors matched the file"


def test_resolve_returns_single_candidate_without_probing(tmp_path: Path):
    target = tmp_path / "file.txt"
    target.write_text("data")
    device = _device("dev1")
    resolver = DeviceResolver(DummyConfigService(matching=[device]), DummyFactory({}))

    resolution = resolver.resolve(target)

    assert resolution.selected == device
    assert resolution.kind is DeviceResolutionKind.ACCEPT
    assert resolution.assessments == tuple()
    assert "probing skipped" in resolution.reason


def test_resolve_all_mismatch(tmp_path: Path):
    target = tmp_path / "file.txt"
    target.write_text("data")
    dev1 = _device("dev1")
    dev2 = _device("dev2")
    factory = DummyFactory(
        {
            "dev1": FileProbeResult.mismatch("nope"),
            "dev2": FileProbeResult.mismatch("nope"),
        }
    )
    resolver = DeviceResolver(DummyConfigService(matching=[dev1, dev2]), factory)

    resolution = resolver.resolve(target)

    assert resolution.selected is None
    assert resolution.kind is DeviceResolutionKind.REJECT
    assert "rejected the file" in resolution.reason
    assert len(resolution.assessments) == 2


def test_resolve_inconclusive_prefers_first_unknown(tmp_path: Path):
    target = tmp_path / "file.txt"
    target.write_text("data")
    dev1 = _device("dev1")
    dev2 = _device("dev2")
    factory = DummyFactory(
        {
            "dev1": FileProbeResult.unknown("inconclusive"),
            "dev2": FileProbeResult.mismatch("nope"),
        }
    )
    resolver = DeviceResolver(DummyConfigService(matching=[dev1, dev2]), factory)

    resolution = resolver.resolve(target)

    assert resolution.selected == dev1
    assert resolution.kind is DeviceResolutionKind.ACCEPT
    assert "inconclusive" in resolution.reason


def test_device_resolution_matched_property_reflects_selection() -> None:
    """Expose a stable bool helper for callers checking match status."""

    matched = DeviceResolution.accept(_device("dev"), reason="ok")
    unmatched = DeviceResolution.reject(reason="none")
    deferred_with_selected = DeviceResolution.defer(
        reason="wait",
        selected=_device("dev"),
        retry_delay=1.0,
    )

    assert matched.matched is True
    assert unmatched.matched is False
    assert deferred_with_selected.matched is False
    assert deferred_with_selected.deferred is True


def test_device_resolution_accept_requires_selected_device() -> None:
    """Guard against ambiguous ACCEPT outcomes without a chosen device."""

    with pytest.raises(ValueError, match="requires a selected device"):
        DeviceResolution(
            selected=None,
            assessments=tuple(),
            reason="bad",
            kind=DeviceResolutionKind.ACCEPT,
        )


def test_retry_delay_falls_back_when_device_value_is_invalid() -> None:
    """Invalid retry values should degrade to resolver defaults."""

    device = _device("dev", retry_delay=1.0)
    device.watcher.retry_delay_seconds = "bad-value"
    resolver = DeviceResolver(DummyConfigService(), DummyFactory({}))

    assert resolver._device_retry_delay(device) == 2.0


def test_should_defer_empty_directory_returns_false_when_directory_has_contents(
    tmp_path: Path,
) -> None:
    """A non-empty folder should not be deferred as pending."""

    target = tmp_path / "has-content"
    target.mkdir()
    (target / "item.txt").write_text("value")

    assert DeviceResolver._should_defer_empty_directory(target) is False


def test_should_defer_empty_directory_handles_missing_path(tmp_path: Path) -> None:
    """Disappeared paths are deferred for retry."""

    missing = tmp_path / "gone"
    assert DeviceResolver._should_defer_empty_directory(missing) is True


def test_should_defer_empty_directory_returns_false_for_regular_files(
    tmp_path: Path,
) -> None:
    """Regular files are not treated as empty directories."""

    target = tmp_path / "file.txt"
    target.write_text("value")

    assert DeviceResolver._should_defer_empty_directory(target) is False


def test_should_defer_empty_directory_defers_on_permission_error(
    monkeypatch, tmp_path: Path, caplog
) -> None:
    """Permission failures while listing a folder should defer processing."""

    target = tmp_path / "restricted"
    target.mkdir()

    def _raise_permission_error(self: Path):
        raise PermissionError("no access")

    monkeypatch.setattr(Path, "iterdir", _raise_permission_error)
    caplog.set_level(logging.DEBUG, logger="dpost.application.processing.device_resolver")

    assert DeviceResolver._should_defer_empty_directory(target) is True
    assert any("lacking permission" in record.message for record in caplog.records)


def test_should_defer_empty_directory_defers_on_os_error(
    monkeypatch, tmp_path: Path, caplog
) -> None:
    """Unexpected OS errors should also keep the path deferred."""

    target = tmp_path / "problematic"
    target.mkdir()

    def _raise_os_error(self: Path):
        raise OSError("io issue")

    monkeypatch.setattr(Path, "iterdir", _raise_os_error)
    caplog.set_level(logging.DEBUG, logger="dpost.application.processing.device_resolver")

    assert DeviceResolver._should_defer_empty_directory(target) is True
    assert any("os error while inspecting" in record.message for record in caplog.records)


def test_probe_wraps_unexpected_processor_error(tmp_path: Path, caplog) -> None:
    """Probe exceptions are captured as UNKNOWN outcomes with warning logs."""

    class _ExplodingProcessor:
        def probe_file(self, filepath: str) -> FileProbeResult:
            raise RuntimeError("explode")

    class _ExplodingFactory:
        def get_for_device(self, device_id: str):
            return _ExplodingProcessor()

    resolver = DeviceResolver(DummyConfigService(), _ExplodingFactory())
    caplog.set_level(logging.WARNING, logger="dpost.application.processing.device_resolver")

    assessment = resolver._probe(_device("dev"), tmp_path / "x.txt")

    assert assessment.result.is_definitive() is False
    assert assessment.result.reason == "explode"
    assert any("probe failed" in record.message for record in caplog.records)


def test_choose_returns_none_when_no_assessments() -> None:
    """Empty candidate sets cannot produce a selected device."""

    assert DeviceResolver._choose([]) is None


def test_choose_prefers_higher_confidence_match() -> None:
    """Higher confidence wins when multiple processors match."""

    high = _device("high")
    low = _device("low")
    assessments = [
        _assessment(low, FileProbeResult.match(confidence=0.3)),
        _assessment(high, FileProbeResult.match(confidence=0.9)),
    ]

    assert DeviceResolver._choose(assessments) == high


def test_select_reappear_device_skips_invalid_window_values() -> None:
    """Candidates with malformed reappear windows should be ignored."""

    bad = _device("bad")
    bad.watcher.reappear_window_seconds = "not-a-float"
    good = _device("good", reappear=5.0)

    assert DeviceResolver._select_reappear_device([bad, good]) == good


def test_build_reason_returns_single_candidate_message_without_assessments(
    tmp_path: Path,
) -> None:
    """No assessments should report the single-selector fallback reason."""

    reason = DeviceResolver._build_reason(
        selected=None,
        assessments=tuple(),
        target=tmp_path / "file.txt",
    )

    assert reason == "Single device matched selectors"


def test_build_reason_reports_no_definitive_probe_match(tmp_path: Path) -> None:
    """Non-mismatch inconclusive probes should keep an explicit no-match reason."""

    dev = _device("dev")
    reason = DeviceResolver._build_reason(
        selected=None,
        assessments=[_assessment(dev, FileProbeResult.unknown("uncertain"))],
        target=tmp_path / "file.txt",
    )

    assert reason == "No definitive probe match"
