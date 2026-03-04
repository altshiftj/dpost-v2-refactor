"""Tracing adapter with correlation context validation and span lifecycle API."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Callable, Mapping
from uuid import uuid4

TraceBackend = Callable[[dict[str, Any]], None]


class TracingError(RuntimeError):
    """Base tracing adapter failure."""


class TracingContextError(TracingError):
    """Raised when required correlation ids are missing/invalid."""


class TracingSpanGraphError(TracingError):
    """Raised when parent-child span relationships are invalid."""


class TracingBackendError(TracingError):
    """Raised when tracing backend emits an error."""


class TracingSerializationError(TracingError):
    """Raised when span metadata cannot be serialized."""


@dataclass(frozen=True, slots=True)
class TraceContext:
    """Correlation context propagated across tracing calls."""

    trace_id: str
    event_id: str
    session_id: str | None = None


@dataclass(frozen=True, slots=True)
class SpanRecord:
    """Immutable span record model."""

    span_id: str
    trace_id: str
    event_id: str
    name: str
    started_at: datetime
    parent_span_id: str | None
    metadata: Mapping[str, Any]
    ended_at: datetime | None = None
    duration_ms: float | None = None


class TracingAdapter:
    """Trace span manager with optional backend emission hook."""

    def __init__(
        self,
        *,
        backend: TraceBackend | None = None,
        span_id_factory: Callable[[], str] | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._backend = backend
        self._span_id_factory = span_id_factory or (lambda: uuid4().hex)
        self._now = now or (lambda: datetime.now(tz=UTC))
        self._active_spans: dict[str, SpanRecord] = {}

    def start_span(
        self,
        *,
        context: TraceContext,
        name: str,
        parent_span_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> SpanRecord:
        """Start a span for given correlation context and optional parent."""
        self._validate_context(context)
        normalized_name = str(name).strip()
        if not normalized_name:
            raise TracingContextError("span name must be non-empty")
        if parent_span_id is not None and parent_span_id not in self._active_spans:
            raise TracingSpanGraphError(
                f"parent span does not exist: {parent_span_id!r}"
            )

        span = SpanRecord(
            span_id=self._span_id_factory(),
            trace_id=context.trace_id.strip(),
            event_id=context.event_id.strip(),
            name=normalized_name,
            started_at=self._now(),
            parent_span_id=parent_span_id,
            metadata=MappingProxyType(_normalize_metadata(metadata or {})),
        )
        self._active_spans[span.span_id] = span
        self._emit_or_raise("start", span)
        return span

    def end_span(self, span_id: str, *, outcome: str) -> SpanRecord:
        """End an active span and emit terminal trace payload."""
        active = self._active_spans.pop(span_id, None)
        if active is None:
            raise TracingSpanGraphError(f"unknown span id: {span_id!r}")

        ended_at = self._now()
        duration_ms = max(0.0, (ended_at - active.started_at).total_seconds() * 1000.0)
        metadata = dict(active.metadata)
        metadata["outcome"] = str(outcome)
        closed = replace(
            active,
            metadata=MappingProxyType(metadata),
            ended_at=ended_at,
            duration_ms=duration_ms,
        )
        self._emit_or_raise("end", closed)
        return closed

    def _emit_or_raise(self, event: str, span: SpanRecord) -> None:
        if self._backend is None:
            return
        payload = {
            "event": event,
            "span_id": span.span_id,
            "trace_id": span.trace_id,
            "event_id": span.event_id,
            "name": span.name,
            "parent_span_id": span.parent_span_id,
            "started_at": span.started_at.isoformat(),
            "ended_at": span.ended_at.isoformat() if span.ended_at else None,
            "duration_ms": span.duration_ms,
            "metadata": dict(span.metadata),
        }
        try:
            self._backend(payload)
        except Exception as exc:  # noqa: BLE001
            raise TracingBackendError(str(exc)) from exc

    @staticmethod
    def _validate_context(context: TraceContext) -> None:
        if not isinstance(context, TraceContext):
            raise TracingContextError("context must be TraceContext")
        if not isinstance(context.trace_id, str) or not context.trace_id.strip():
            raise TracingContextError("trace_id must be non-empty")
        if not isinstance(context.event_id, str) or not context.event_id.strip():
            raise TracingContextError("event_id must be non-empty")


def _normalize_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(metadata, Mapping):
        raise TracingSerializationError("span metadata must be mapping")
    return {str(key): _normalize_primitive(value) for key, value in metadata.items()}


def _normalize_primitive(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _normalize_primitive(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_normalize_primitive(item) for item in value]
    raise TracingSerializationError(f"unsupported metadata type: {type(value)!r}")
