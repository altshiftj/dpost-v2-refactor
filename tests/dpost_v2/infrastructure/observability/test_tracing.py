from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from dpost_v2.infrastructure.observability.tracing import (
    TraceContext,
    TracingAdapter,
    TracingBackendError,
    TracingContextError,
    TracingSerializationError,
    TracingSpanGraphError,
)


@dataclass(frozen=True)
class _Opaque:
    value: str


def test_tracing_span_lifecycle_maintains_parent_child_relationships() -> None:
    emitted: list[dict[str, Any]] = []
    tracer = TracingAdapter(backend=lambda payload: emitted.append(payload))
    context = TraceContext(trace_id="trace-1", event_id="event-1")

    root = tracer.start_span(context=context, name="ingestion")
    child = tracer.start_span(
        context=context,
        name="persist",
        parent_span_id=root.span_id,
    )
    closed_child = tracer.end_span(child.span_id, outcome="ok")
    closed_root = tracer.end_span(root.span_id, outcome="ok")

    assert child.parent_span_id == root.span_id
    assert closed_child.duration_ms >= 0
    assert closed_root.duration_ms >= 0
    assert len(emitted) == 4


def test_tracing_requires_non_empty_correlation_ids() -> None:
    tracer = TracingAdapter()

    with pytest.raises(TracingContextError):
        tracer.start_span(
            context=TraceContext(trace_id="", event_id="event-1"), name="x"
        )


def test_tracing_rejects_unknown_parent_spans() -> None:
    tracer = TracingAdapter()
    context = TraceContext(trace_id="trace-1", event_id="event-1")

    with pytest.raises(TracingSpanGraphError):
        tracer.start_span(context=context, name="x", parent_span_id="missing")


def test_tracing_rejects_non_serializable_metadata() -> None:
    tracer = TracingAdapter()
    context = TraceContext(trace_id="trace-1", event_id="event-1")

    with pytest.raises(TracingSerializationError):
        tracer.start_span(context=context, name="x", metadata={"opaque": _Opaque("x")})


def test_tracing_maps_backend_failures() -> None:
    tracer = TracingAdapter(
        backend=lambda payload: (_ for _ in ()).throw(RuntimeError("down"))
    )
    context = TraceContext(trace_id="trace-1", event_id="event-1")

    with pytest.raises(TracingBackendError):
        tracer.start_span(context=context, name="x")
