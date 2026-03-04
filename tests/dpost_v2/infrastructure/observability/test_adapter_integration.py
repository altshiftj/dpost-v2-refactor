from __future__ import annotations

from typing import Any

from dpost_v2.infrastructure.observability.logging import (
    StructuredLoggingConfig,
    build_structured_logger,
)
from dpost_v2.infrastructure.observability.metrics import MetricsAdapter
from dpost_v2.infrastructure.observability.tracing import TraceContext, TracingAdapter


def test_observability_adapters_share_correlation_and_contain_metric_backend_failure() -> None:
    trace_events: list[dict[str, Any]] = []
    log_entries: list[dict[str, Any]] = []

    tracer = TracingAdapter(backend=lambda payload: trace_events.append(payload))
    logger = build_structured_logger(
        StructuredLoggingConfig(runtime_metadata={"service": "dpost"}),
        sink=lambda entry: log_entries.append(entry),
    )
    metrics = MetricsAdapter(
        namespace="dpost",
        backend=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("metrics down")),
    )

    context = TraceContext(trace_id="trace-1", event_id="event-1")
    span = tracer.start_span(context=context, name="persist")
    log_status = logger.emit(
        level="info",
        message="persist started",
        payload={"record_id": "rec-1"},
        correlation={"trace_id": context.trace_id, "event_id": context.event_id},
    )
    metric_status = metrics.emit_counter(
        "ingestion.persist",
        value=1,
        tags={"stage": "persist", "result": "started"},
    )
    tracer.end_span(span.span_id, outcome="ok")

    assert log_status["status"] == "emitted"
    assert metric_status["status"] == "backend_error"
    assert len(trace_events) == 2
    assert trace_events[0]["trace_id"] == "trace-1"
    assert trace_events[1]["trace_id"] == "trace-1"
    assert log_entries[0]["correlation"]["trace_id"] == "trace-1"
