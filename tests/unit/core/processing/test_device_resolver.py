from __future__ import annotations

from pathlib import Path

from dpost.application.config import DeviceConfig, WatcherSettings
from dpost.application.processing.device_resolver import DeviceResolver
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


def test_resolve_missing_path_selects_reappear_device(tmp_path: Path):
    target = tmp_path / "missing.txt"
    device = _device("dev1", reappear=1.0)
    resolver = DeviceResolver(DummyConfigService(matching=[device]), DummyFactory({}))

    resolution = resolver.resolve(target)

    assert resolution.selected == device
    assert "waiting for reappearance" in resolution.reason


def test_resolve_missing_path_defers_without_reappear(tmp_path: Path):
    target = tmp_path / "missing.txt"
    device = _device("dev1", reappear=0.0)
    resolver = DeviceResolver(DummyConfigService(matching=[device]), DummyFactory({}))

    resolution = resolver.resolve(target)

    assert resolution.selected is None
    assert resolution.deferred is True
    assert "disappeared" in resolution.reason


def test_resolve_defers_for_deferred_devices(tmp_path: Path):
    target = tmp_path / "file.txt"
    target.write_text("data")
    device = _device("dev1", retry_delay=4.5)
    resolver = DeviceResolver(DummyConfigService(matching=[], deferred=[device]), DummyFactory({}))

    resolution = resolver.resolve(target)

    assert resolution.deferred is True
    assert resolution.retry_delay == 4.5
    assert "dev1" in resolution.reason


def test_resolve_defers_for_empty_directory(tmp_path: Path):
    target = tmp_path / "empty"
    target.mkdir()
    resolver = DeviceResolver(DummyConfigService(matching=[], deferred=[]), DummyFactory({}))

    resolution = resolver.resolve(target)

    assert resolution.deferred is True
    assert "Deferred until" in resolution.reason


def test_resolve_returns_single_candidate_without_probing(tmp_path: Path):
    target = tmp_path / "file.txt"
    target.write_text("data")
    device = _device("dev1")
    resolver = DeviceResolver(DummyConfigService(matching=[device]), DummyFactory({}))

    resolution = resolver.resolve(target)

    assert resolution.selected == device
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
    assert "inconclusive" in resolution.reason
