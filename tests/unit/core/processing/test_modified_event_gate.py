from __future__ import annotations


from ipat_watchdog.core.processing.modified_event_gate import ModifiedEventGate


class DummyConfigService:
    def __init__(self, devices):
        self._devices = devices

    def matching_devices(self, path_like):
        return list(self._devices)


class DummyProcessor:
    def __init__(self, allow=True, raise_exc=False):
        self._allow = allow
        self._raise = raise_exc

    def should_queue_modified(self, path):
        if self._raise:
            raise RuntimeError("boom")
        return self._allow


class FakeClock:
    def __init__(self, value=0.0):
        self.value = value

    def __call__(self):
        return self.value


def test_should_queue_skips_directories(tmp_path):
    target = tmp_path / "folder"
    target.mkdir()

    gate = ModifiedEventGate(
        config_service=DummyConfigService([object()]),
        processor_resolver=lambda device: DummyProcessor(allow=True),
    )

    assert gate.should_queue(str(target)) is False


def test_should_queue_returns_false_without_candidates(tmp_path):
    target = tmp_path / "sample.txt"
    target.write_text("data")

    gate = ModifiedEventGate(
        config_service=DummyConfigService([]),
        processor_resolver=lambda device: DummyProcessor(allow=True),
    )

    assert gate.should_queue(str(target)) is False


def test_should_queue_respects_cooldown(tmp_path):
    clock = FakeClock(0.0)
    target = tmp_path / "sample.txt"
    target.write_text("data")

    gate = ModifiedEventGate(
        config_service=DummyConfigService([object()]),
        processor_resolver=lambda device: DummyProcessor(allow=True),
        cooldown_seconds=5.0,
        prune_after_seconds=100.0,
        prune_interval_seconds=100.0,
        clock=clock,
    )

    assert gate.should_queue(str(target)) is True

    clock.value = 1.0
    assert gate.should_queue(str(target)) is False

    clock.value = 6.0
    assert gate.should_queue(str(target)) is True


def test_should_queue_handles_processor_exception(tmp_path):
    target = tmp_path / "sample.txt"
    target.write_text("data")

    gate = ModifiedEventGate(
        config_service=DummyConfigService([object()]),
        processor_resolver=lambda device: DummyProcessor(raise_exc=True),
    )

    assert gate.should_queue(str(target)) is False


def test_maybe_prune_removes_stale():
    clock = FakeClock(0.0)
    gate = ModifiedEventGate(
        config_service=DummyConfigService([]),
        processor_resolver=lambda device: DummyProcessor(),
        cooldown_seconds=1.0,
        prune_after_seconds=2.0,
        prune_interval_seconds=2.0,
        clock=clock,
    )

    gate._last_seen = {"old": 0.0, "new": 5.0}
    gate._next_prune_at = 0.0

    gate._maybe_prune(now=6.0)

    assert "old" not in gate._last_seen
    assert "new" in gate._last_seen
