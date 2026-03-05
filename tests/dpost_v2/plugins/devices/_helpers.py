from __future__ import annotations

from datetime import UTC, datetime

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext


def processing_context_for(source_path: str) -> ProcessingContext:
    runtime_context = RuntimeContext.from_settings(
        settings={
            "mode": "headless",
            "profile": "prod",
            "session_id": "session-parity-spec",
            "event_id": "event-parity-spec",
            "trace_id": "trace-parity-spec",
        },
        dependency_ids={"clock": "clock-1", "ui": "ui-1", "sync": "sync-1"},
    )
    return ProcessingContext.for_candidate(
        runtime_context=runtime_context,
        candidate_event={
            "source_path": source_path,
            "event_type": "created",
            "observed_at": datetime(2026, 3, 5, 12, 0, tzinfo=UTC),
        },
    )
