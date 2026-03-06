from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping

import pytest

from dpost_v2.application.contracts.context import ProcessingContext
from dpost_v2.application.ingestion.engine import IngestionOutcome, IngestionOutcomeKind
from dpost_v2.application.runtime.dpost_app import DPostApp
from dpost_v2.application.session.session_manager import (
    SessionManager,
    SessionPolicy,
    SessionStateKind,
)


@dataclass
class FakeClock:
    current: datetime

    def now(self) -> datetime:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current = self.current + timedelta(seconds=float(seconds))


@dataclass
class FakeEngine:
    outcomes: list[IngestionOutcome[object]]
    on_process: Any = None

    def __post_init__(self) -> None:
        self.seen_event_ids: list[str] = []
        self.seen_processing_contexts: list[ProcessingContext] = []
        self._index = 0

    def process(
        self,
        *,
        event: Mapping[str, Any],
        processing_context: ProcessingContext | None = None,
    ) -> IngestionOutcome[object]:
        self.seen_event_ids.append(str(event["event_id"]))
        if processing_context is not None:
            self.seen_processing_contexts.append(processing_context)
        if callable(self.on_process):
            self.on_process(event, processing_context)
        outcome = self.outcomes[self._index]
        self._index += 1
        return outcome


def _outcome(kind: IngestionOutcomeKind) -> IngestionOutcome[object]:
    return IngestionOutcome(
        kind=kind,
        final_stage_id=None,
        state=None,
        stage_trace=(),
        retry_plan=None,
        emission_status="skipped",
    )


def _event(event_id: str, *, path: str = "/tmp/file.txt") -> Mapping[str, object]:
    return {
        "event_id": event_id,
        "path": path,
        "event_kind": "created",
    }


@dataclass
class PollingSource:
    batches: list[list[Mapping[str, object]]]

    def __post_init__(self) -> None:
        self.calls = 0

    def __call__(self) -> list[Mapping[str, object]]:
        self.calls += 1
        if self.calls <= len(self.batches):
            return self.batches[self.calls - 1]
        return []


def test_runtime_app_processes_events_in_order_and_emits_terminal_event() -> None:
    clock = FakeClock(datetime(2026, 3, 4, 10, 0, tzinfo=UTC))
    session_manager = SessionManager(policy=SessionPolicy(), clock=clock)
    engine = FakeEngine(
        outcomes=[
            _outcome(IngestionOutcomeKind.SUCCEEDED),
            _outcome(IngestionOutcomeKind.DEFERRED_RETRY),
        ]
    )
    emitted: list[Mapping[str, object]] = []

    app = DPostApp(
        session_manager=session_manager,
        ingestion_engine=engine,
        event_source=[_event("evt-001"), _event("evt-002")],
        event_emitter=emitted.append,
        clock=clock,
        session_id="session-001",
        trace_id="trace-001",
    )

    result = app.run()

    assert engine.seen_event_ids == ["evt-001", "evt-002"]
    assert result.processed_count == 2
    assert result.skipped_count == 0
    assert result.failed_count == 0
    assert result.terminal_reason == "end_of_stream"
    assert emitted[0]["kind"] == "runtime_started"
    assert emitted[-1]["kind"] == "runtime_completed"
    assert emitted[-1]["reason_code"] == "end_of_stream"
    assert session_manager.state.kind is SessionStateKind.COMPLETED


def test_runtime_app_treats_deferred_stage_as_non_failure_and_emits_deferred_event() -> (
    None
):
    clock = FakeClock(datetime(2026, 3, 4, 10, 5, tzinfo=UTC))
    session_manager = SessionManager(policy=SessionPolicy(), clock=clock)
    engine = FakeEngine(
        outcomes=[_outcome(IngestionOutcomeKind.DEFERRED_STAGE)],
    )
    emitted: list[Mapping[str, object]] = []

    app = DPostApp(
        session_manager=session_manager,
        ingestion_engine=engine,
        event_source=[_event("evt-stage-001")],
        event_emitter=emitted.append,
        clock=clock,
        session_id="session-stage-001",
        trace_id="trace-stage-001",
    )

    result = app.run()

    assert result.processed_count == 1
    assert result.failed_count == 0
    assert result.terminal_reason == "end_of_stream"
    assert any(event.get("kind") == "ingestion_deferred" for event in emitted)


def test_runtime_app_skips_duplicate_event_ids() -> None:
    clock = FakeClock(datetime(2026, 3, 4, 11, 0, tzinfo=UTC))
    session_manager = SessionManager(policy=SessionPolicy(), clock=clock)
    engine = FakeEngine(outcomes=[_outcome(IngestionOutcomeKind.SUCCEEDED)])
    emitted: list[Mapping[str, object]] = []

    app = DPostApp(
        session_manager=session_manager,
        ingestion_engine=engine,
        event_source=[_event("evt-010"), _event("evt-010")],
        event_emitter=emitted.append,
        clock=clock,
        session_id="session-010",
        trace_id="trace-010",
    )

    result = app.run()

    assert engine.seen_event_ids == ["evt-010"]
    assert result.processed_count == 1
    assert result.skipped_count == 1
    assert any(event["kind"] == "runtime_event_skipped" for event in emitted)
    assert emitted[-1]["kind"] == "runtime_completed"


def test_runtime_app_stops_on_cancellation_signal() -> None:
    clock = FakeClock(datetime(2026, 3, 4, 12, 0, tzinfo=UTC))
    session_manager = SessionManager(policy=SessionPolicy(), clock=clock)
    engine = FakeEngine(
        outcomes=[
            _outcome(IngestionOutcomeKind.SUCCEEDED),
            _outcome(IngestionOutcomeKind.SUCCEEDED),
        ]
    )
    emitted: list[Mapping[str, object]] = []
    cancellation_checks = {"count": 0}

    def cancellation_signal() -> bool:
        cancellation_checks["count"] += 1
        return cancellation_checks["count"] > 1

    app = DPostApp(
        session_manager=session_manager,
        ingestion_engine=engine,
        event_source=[_event("evt-020"), _event("evt-021")],
        event_emitter=emitted.append,
        clock=clock,
        session_id="session-020",
        trace_id="trace-020",
        cancellation_signal=cancellation_signal,
    )

    result = app.run()

    assert engine.seen_event_ids == ["evt-020"]
    assert result.processed_count == 1
    assert result.terminal_reason == "cancelled"
    assert emitted[-1]["kind"] == "runtime_cancelled"


def test_runtime_app_emits_failure_terminal_event_and_aborts_session() -> None:
    clock = FakeClock(datetime(2026, 3, 4, 13, 0, tzinfo=UTC))
    session_manager = SessionManager(policy=SessionPolicy(), clock=clock)
    engine = FakeEngine(outcomes=[_outcome(IngestionOutcomeKind.FAILED_TERMINAL)])
    emitted: list[Mapping[str, object]] = []

    app = DPostApp(
        session_manager=session_manager,
        ingestion_engine=engine,
        event_source=[_event("evt-030")],
        event_emitter=emitted.append,
        clock=clock,
        session_id="session-030",
        trace_id="trace-030",
    )

    result = app.run()

    assert result.processed_count == 1
    assert result.failed_count == 1
    assert result.terminal_reason == "failed_terminal"
    assert emitted[-1]["kind"] == "runtime_failed"
    assert session_manager.state.kind is SessionStateKind.ABORTED


def test_runtime_app_raises_when_event_missing_event_id() -> None:
    clock = FakeClock(datetime(2026, 3, 4, 14, 0, tzinfo=UTC))
    session_manager = SessionManager(policy=SessionPolicy(), clock=clock)
    engine = FakeEngine(outcomes=[_outcome(IngestionOutcomeKind.SUCCEEDED)])

    app = DPostApp(
        session_manager=session_manager,
        ingestion_engine=engine,
        event_source=[{"path": "/tmp/missing-id"}],
        event_emitter=lambda _event: None,
        clock=clock,
        session_id="session-040",
        trace_id="trace-040",
    )

    with pytest.raises(ValueError, match="event_id"):
        app.run()


def test_runtime_app_derives_processing_context_for_each_event() -> None:
    clock = FakeClock(datetime(2026, 3, 4, 14, 30, tzinfo=UTC))
    session_manager = SessionManager(policy=SessionPolicy(), clock=clock)
    engine = FakeEngine(
        outcomes=[_outcome(IngestionOutcomeKind.SUCCEEDED)],
    )
    emitted: list[Mapping[str, object]] = []

    app = DPostApp(
        session_manager=session_manager,
        ingestion_engine=engine,
        event_source=[
            {
                "event_id": "evt-ctx-001",
                "path": "/tmp/context-file.txt",
                "event_kind": "modified",
                "observed_at": datetime(2026, 3, 4, 14, 29, tzinfo=UTC),
            }
        ],
        event_emitter=emitted.append,
        clock=clock,
        session_id="session-ctx-001",
        trace_id="trace-ctx-001",
        mode="headless",
        profile="ci",
    )

    app.run()

    assert len(engine.seen_processing_contexts) == 1
    context = engine.seen_processing_contexts[0]
    assert context.source_path == "/tmp/context-file.txt"
    assert context.event_type == "modified"
    assert context.runtime_context.mode == "headless"
    assert context.runtime_context.profile == "ci"
    assert context.runtime_context.session_id == "session-ctx-001"


def test_runtime_app_emits_canonical_ingestion_event_for_success_outcome() -> None:
    clock = FakeClock(datetime(2026, 3, 4, 14, 40, tzinfo=UTC))
    session_manager = SessionManager(policy=SessionPolicy(), clock=clock)
    engine = FakeEngine(outcomes=[_outcome(IngestionOutcomeKind.SUCCEEDED)])
    emitted: list[Mapping[str, object]] = []

    app = DPostApp(
        session_manager=session_manager,
        ingestion_engine=engine,
        event_source=[_event("evt-evt-001", path="/tmp/file-a.txt")],
        event_emitter=emitted.append,
        clock=clock,
        session_id="session-evt-001",
        trace_id="trace-evt-001",
    )

    app.run()

    assert any(event.get("kind") == "ingestion_succeeded" for event in emitted)


def test_runtime_app_hard_timeout_aborts_before_next_event() -> None:
    clock = FakeClock(datetime(2026, 3, 4, 15, 0, tzinfo=UTC))
    session_manager = SessionManager(
        policy=SessionPolicy(idle_timeout_seconds=30.0, max_runtime_seconds=1.0),
        clock=clock,
    )

    def on_process(
        _event: Mapping[str, Any], _context: ProcessingContext | None
    ) -> None:
        clock.current = clock.current + timedelta(seconds=2)

    engine = FakeEngine(
        outcomes=[
            _outcome(IngestionOutcomeKind.SUCCEEDED),
            _outcome(IngestionOutcomeKind.SUCCEEDED),
        ],
        on_process=on_process,
    )
    emitted: list[Mapping[str, object]] = []

    app = DPostApp(
        session_manager=session_manager,
        ingestion_engine=engine,
        event_source=[_event("evt-time-001"), _event("evt-time-002")],
        event_emitter=emitted.append,
        clock=clock,
        session_id="session-time-001",
        trace_id="trace-time-001",
    )

    result = app.run()

    assert engine.seen_event_ids == ["evt-time-001"]
    assert result.terminal_reason == "hard_timeout"
    assert emitted[-1]["kind"] == "runtime_failed"
    assert emitted[-1]["reason_code"] == "hard_timeout"


def test_runtime_app_oneshot_mode_consumes_single_polled_batch() -> None:
    clock = FakeClock(datetime(2026, 3, 6, 9, 0, tzinfo=UTC))
    session_manager = SessionManager(policy=SessionPolicy(), clock=clock)
    engine = FakeEngine(outcomes=[_outcome(IngestionOutcomeKind.SUCCEEDED)])
    source = PollingSource(
        batches=[
            [_event("evt-loop-001")],
            [_event("evt-loop-002")],
        ]
    )

    app = DPostApp(
        session_manager=session_manager,
        ingestion_engine=engine,
        event_source=source,
        event_emitter=lambda _event: None,
        clock=clock,
        session_id="session-loop-001",
        trace_id="trace-loop-001",
        loop_mode="oneshot",
    )

    result = app.run()

    assert source.calls == 1
    assert engine.seen_event_ids == ["evt-loop-001"]
    assert result.processed_count == 1
    assert result.terminal_reason == "end_of_stream"


def test_runtime_app_continuous_mode_polls_until_cancellation_and_processes_late_event() -> (
    None
):
    clock = FakeClock(datetime(2026, 3, 6, 9, 5, tzinfo=UTC))
    session_manager = SessionManager(policy=SessionPolicy(), clock=clock)
    engine = FakeEngine(outcomes=[_outcome(IngestionOutcomeKind.SUCCEEDED)])
    source = PollingSource(
        batches=[
            [],
            [_event("evt-loop-late-001")],
            [],
        ]
    )
    cancellation_checks = {"count": 0}

    def cancellation_signal() -> bool:
        cancellation_checks["count"] += 1
        return source.calls >= 3 and cancellation_checks["count"] > 3

    app = DPostApp(
        session_manager=session_manager,
        ingestion_engine=engine,
        event_source=source,
        event_emitter=lambda _event: None,
        clock=clock,
        session_id="session-loop-late-001",
        trace_id="trace-loop-late-001",
        loop_mode="continuous",
        poll_interval_seconds=0.5,
        cancellation_signal=cancellation_signal,
    )

    result = app.run()

    assert source.calls >= 3
    assert engine.seen_event_ids == ["evt-loop-late-001"]
    assert result.processed_count == 1
    assert result.terminal_reason == "cancelled"


def test_runtime_app_continuous_mode_soft_times_out_while_idle_without_wall_clock_sleep() -> (
    None
):
    clock = FakeClock(datetime(2026, 3, 6, 9, 10, tzinfo=UTC))
    session_manager = SessionManager(
        policy=SessionPolicy(idle_timeout_seconds=2.0),
        clock=clock,
    )
    engine = FakeEngine(outcomes=[])
    source = PollingSource(batches=[[], [], []])

    app = DPostApp(
        session_manager=session_manager,
        ingestion_engine=engine,
        event_source=source,
        event_emitter=lambda _event: None,
        clock=clock,
        session_id="session-loop-idle-001",
        trace_id="trace-loop-idle-001",
        loop_mode="continuous",
        poll_interval_seconds=1.0,
    )

    result = app.run()

    assert source.calls >= 2
    assert result.processed_count == 0
    assert result.terminal_reason == "soft_timeout"


def test_runtime_app_continuous_mode_skips_duplicate_event_ids_across_poll_cycles() -> (
    None
):
    clock = FakeClock(datetime(2026, 3, 6, 9, 15, tzinfo=UTC))
    session_manager = SessionManager(policy=SessionPolicy(), clock=clock)
    engine = FakeEngine(outcomes=[_outcome(IngestionOutcomeKind.SUCCEEDED)])
    source = PollingSource(
        batches=[
            [_event("evt-loop-dup-001")],
            [_event("evt-loop-dup-001")],
            [],
        ]
    )

    def cancellation_signal() -> bool:
        return source.calls >= 3

    app = DPostApp(
        session_manager=session_manager,
        ingestion_engine=engine,
        event_source=source,
        event_emitter=lambda _event: None,
        clock=clock,
        session_id="session-loop-dup-001",
        trace_id="trace-loop-dup-001",
        loop_mode="continuous",
        poll_interval_seconds=0.0,
        cancellation_signal=cancellation_signal,
    )

    result = app.run()

    assert engine.seen_event_ids == ["evt-loop-dup-001"]
    assert result.processed_count == 1
    assert result.skipped_count == 1


def test_runtime_app_shutdown_hook_is_idempotent() -> None:
    clock = FakeClock(datetime(2026, 3, 6, 9, 20, tzinfo=UTC))
    session_manager = SessionManager(policy=SessionPolicy(), clock=clock)
    engine = FakeEngine(outcomes=[])
    shutdown_calls: list[str] = []

    app = DPostApp(
        session_manager=session_manager,
        ingestion_engine=engine,
        event_source=[],
        event_emitter=lambda _event: None,
        clock=clock,
        session_id="session-shutdown-001",
        trace_id="trace-shutdown-001",
        shutdown_hook=lambda: shutdown_calls.append("shutdown"),
    )

    app.shutdown()
    app.shutdown()

    assert shutdown_calls == ["shutdown"]
