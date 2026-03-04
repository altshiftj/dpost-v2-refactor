from __future__ import annotations

from dpost_v2.application.ingestion.policies.failure_emitter import (
    EmissionStatus,
    emit_failure_event,
)
from dpost_v2.application.ingestion.policies.failure_outcome import (
    FailureTerminalType,
    build_failure_outcome,
)
from dpost_v2.application.ingestion.policies.immediate_sync_error_emitter import (
    emit_immediate_sync_failure,
)


def test_failure_emitter_returns_emitted_status() -> None:
    captured: dict[str, object] = {}

    def event_port(payload: dict[str, object]) -> None:
        captured.update(payload)

    outcome = build_failure_outcome(
        classification=type(
            "C",
            (),
            {
                "stage_id": "persist",
                "reason_code": "io_error",
                "severity": "error",
            },
        )(),
        terminal_type=FailureTerminalType.FAILED,
    )

    result = emit_failure_event(
        failure_outcome=outcome,
        correlation_context={"event_id": "e1"},
        event_port=event_port,
    )

    assert result.status is EmissionStatus.EMITTED
    assert captured["reason_code"] == "io_error"


def test_immediate_sync_error_emission_is_once_per_event() -> None:
    emissions: list[str] = []

    def sink(payload: dict[str, object]) -> None:
        emissions.append(str(payload["event_id"]))

    first = emit_immediate_sync_failure(
        event_id="e1",
        record_id="r1",
        error=RuntimeError("sync"),
        event_port=sink,
    )
    second = emit_immediate_sync_failure(
        event_id="e1",
        record_id="r1",
        error=RuntimeError("sync"),
        event_port=sink,
    )

    assert first.emission_result.status is EmissionStatus.EMITTED
    assert second.emission_result.status is EmissionStatus.SUPPRESSED
    assert emissions == ["e1"]
