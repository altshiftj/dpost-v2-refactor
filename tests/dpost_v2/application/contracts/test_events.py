"""Contract tests for V2 application event models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext
from dpost_v2.application.contracts.events import (
    BaseEvent,
    EventContractError,
    EventKind,
    EventSerializationError,
    EventSeverity,
    EventStage,
    EventValidationError,
    IngestionDeferred,
    IngestionFailed,
    IngestionSucceeded,
    StartupFailed,
    SyncTriggered,
    UnsupportedOutcomeError,
    event_from_outcome,
    to_payload,
)


def _runtime_context() -> RuntimeContext:
    return RuntimeContext.from_settings(
        settings={
            "mode": "headless",
            "profile": "default",
            "session_id": "session-1",
            "event_id": "runtime-event-1",
            "trace_id": "trace-1",
        },
        dependency_ids={"clock": "clock-1", "ui": "ui-1", "sync": "sync-1"},
    )


def _processing_context() -> ProcessingContext:
    return ProcessingContext.for_candidate(
        runtime_context=_runtime_context(),
        candidate_event={
            "source_path": "D:/incoming/file.tif",
            "event_type": "created",
            "observed_at": datetime(2026, 3, 4, 9, 30, tzinfo=UTC),
            "event_id": "evt-10",
            "trace_id": "trace-10",
        },
    )


def test_event_enum_wire_values_are_stable() -> None:
    assert EventKind.INGESTION_SUCCEEDED.value == "ingestion_succeeded"
    assert EventKind.INGESTION_FAILED.value == "ingestion_failed"
    assert EventSeverity.INFO.value == "info"
    assert EventSeverity.ERROR.value == "error"
    assert EventStage.INGESTION.value == "ingestion"
    assert EventStage.STARTUP.value == "startup"


def test_base_event_rejects_missing_correlation_fields() -> None:
    with pytest.raises(EventValidationError, match="event_id"):
        BaseEvent(
            event_id="",
            trace_id="trace-1",
            occurred_at=datetime(2026, 3, 4, tzinfo=UTC),
            stage=EventStage.RUNTIME,
            kind=EventKind.SYNC_TRIGGERED,
            severity=EventSeverity.INFO,
            payload={},
        )


def test_base_event_rejects_non_serializable_payload() -> None:
    with pytest.raises(EventSerializationError):
        BaseEvent(
            event_id="evt-1",
            trace_id="trace-1",
            occurred_at=datetime(2026, 3, 4, tzinfo=UTC),
            stage=EventStage.INGESTION,
            kind=EventKind.INGESTION_SUCCEEDED,
            severity=EventSeverity.INFO,
            payload={"bad": object()},
        )


def test_base_event_rejects_naive_datetime() -> None:
    with pytest.raises(EventValidationError, match="timezone-aware"):
        BaseEvent(
            event_id="evt-1",
            trace_id="trace-1",
            occurred_at=datetime(2026, 3, 4),
            stage=EventStage.INGESTION,
            kind=EventKind.INGESTION_SUCCEEDED,
            severity=EventSeverity.INFO,
            payload={},
        )


def test_event_from_outcome_maps_ingestion_success_deterministically() -> None:
    context = _processing_context()
    occurred_at = datetime(2026, 3, 4, 11, 0, tzinfo=UTC)
    outcome = {
        "status": "succeeded",
        "candidate_id": "cand-123",
        "occurred_at": occurred_at,
    }

    event_one = event_from_outcome(outcome, context)
    event_two = event_from_outcome(outcome, context)

    assert isinstance(event_one, IngestionSucceeded)
    assert event_one == event_two
    assert event_one.event_id == "evt-10"
    assert event_one.trace_id == "trace-10"
    assert event_one.occurred_at == occurred_at


def test_event_from_outcome_maps_failure_with_reason_code() -> None:
    context = _processing_context()
    event = event_from_outcome(
        {"status": "failed", "reason_code": "stage_contract_violation"},
        context,
    )

    assert isinstance(event, IngestionFailed)
    assert event.severity is EventSeverity.ERROR
    assert event.payload["reason_code"] == "stage_contract_violation"


def test_event_from_outcome_maps_deferred_retry_to_warning_event() -> None:
    context = _processing_context()
    event = event_from_outcome(
        {"status": "deferred_retry", "reason_code": "stabilizing"},
        context,
    )

    assert isinstance(event, IngestionDeferred)
    assert event.severity is EventSeverity.WARNING
    assert event.payload["reason_code"] == "stabilizing"


def test_event_from_outcome_maps_deferred_stage_to_warning_event() -> None:
    context = _processing_context()
    event = event_from_outcome(
        {"status": "deferred_stage", "reason_code": "awaiting_pair"},
        context,
    )

    assert isinstance(event, IngestionDeferred)
    assert event.severity is EventSeverity.WARNING
    assert event.payload["reason_code"] == "awaiting_pair"


def test_event_from_outcome_maps_sync_and_startup_statuses() -> None:
    processing_context = _processing_context()
    runtime_context = _runtime_context()

    sync_event = event_from_outcome({"status": "sync_triggered"}, processing_context)
    startup_event = event_from_outcome(
        {"status": "startup_failed", "reason_code": "missing_binding"},
        runtime_context,
    )

    assert isinstance(sync_event, SyncTriggered)
    assert isinstance(startup_event, StartupFailed)
    assert startup_event.payload["reason_code"] == "missing_binding"


def test_event_from_outcome_rejects_unknown_status() -> None:
    with pytest.raises(UnsupportedOutcomeError):
        event_from_outcome({"status": "unknown"}, _processing_context())


def test_to_payload_serializes_contract_event_shape() -> None:
    event = IngestionSucceeded(
        event_id="evt-100",
        trace_id="trace-100",
        occurred_at=datetime(2026, 3, 4, 12, 0, tzinfo=UTC),
        payload={"candidate_id": "cand-100"},
    )

    payload = to_payload(event)

    assert payload == {
        "event_id": "evt-100",
        "trace_id": "trace-100",
        "occurred_at": "2026-03-04T12:00:00+00:00",
        "stage": "ingestion",
        "kind": "ingestion_succeeded",
        "severity": "info",
        "payload": {"candidate_id": "cand-100"},
    }


def test_to_payload_rejects_unknown_event_type() -> None:
    with pytest.raises(EventContractError):
        to_payload(object())  # type: ignore[arg-type]
