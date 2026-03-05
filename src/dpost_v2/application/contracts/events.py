"""Event and message contracts shared across V2 runtime/application lanes."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext


class EventContractError(ValueError):
    """Base exception for event contract failures."""


class EventValidationError(EventContractError):
    """Raised when required event fields are missing or malformed."""


class EventSerializationError(EventContractError):
    """Raised when payload data cannot be serialized safely."""


class UnsupportedOutcomeError(EventContractError):
    """Raised when event factory receives an unsupported outcome type."""


class EventKind(StrEnum):
    """Canonical event kinds used as stable wire values."""

    INGESTION_SUCCEEDED = "ingestion_succeeded"
    INGESTION_DEFERRED = "ingestion_deferred"
    INGESTION_FAILED = "ingestion_failed"
    SYNC_TRIGGERED = "sync_triggered"
    STARTUP_FAILED = "startup_failed"


class EventSeverity(StrEnum):
    """Severity taxonomy for downstream observability and UI layers."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class EventStage(StrEnum):
    """Source stage of event emission."""

    STARTUP = "startup"
    RUNTIME = "runtime"
    INGESTION = "ingestion"
    SYNC = "sync"


def _normalize_primitive(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _normalize_primitive(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_normalize_primitive(item) for item in value]
    if is_dataclass(value):
        result: dict[str, Any] = {}
        for data_field in fields(value):
            result[data_field.name] = _normalize_primitive(
                getattr(value, data_field.name)
            )
        return result
    raise EventSerializationError(f"non-serializable payload value: {type(value)!r}")


def _freeze_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    normalized = _normalize_primitive(dict(payload))
    if not isinstance(normalized, dict):
        raise EventSerializationError("event payload must serialize to a mapping")
    return MappingProxyType(normalized)


@dataclass(frozen=True, slots=True)
class BaseEvent:
    """Shared event fields with validation for all event variants."""

    event_id: str
    trace_id: str
    occurred_at: datetime
    stage: EventStage
    kind: EventKind
    severity: EventSeverity
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, str) or not self.event_id.strip():
            raise EventValidationError("event_id must be a non-empty string")
        if not isinstance(self.trace_id, str) or not self.trace_id.strip():
            raise EventValidationError("trace_id must be a non-empty string")
        if not isinstance(self.occurred_at, datetime):
            raise EventValidationError("occurred_at must be a datetime")
        if self.occurred_at.tzinfo is None:
            raise EventValidationError("occurred_at must be timezone-aware")
        if not isinstance(self.stage, EventStage):
            raise EventValidationError("stage must be EventStage")
        if not isinstance(self.kind, EventKind):
            raise EventValidationError("kind must be EventKind")
        if not isinstance(self.severity, EventSeverity):
            raise EventValidationError("severity must be EventSeverity")
        if not isinstance(self.payload, Mapping):
            raise EventValidationError("payload must be a mapping")
        object.__setattr__(self, "payload", _freeze_payload(self.payload))


@dataclass(frozen=True, slots=True)
class IngestionSucceeded(BaseEvent):
    """Event emitted when ingestion completes successfully."""

    stage: EventStage = EventStage.INGESTION
    kind: EventKind = EventKind.INGESTION_SUCCEEDED
    severity: EventSeverity = EventSeverity.INFO
    payload: Mapping[str, Any] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class IngestionDeferred(BaseEvent):
    """Event emitted when ingestion is deferred for retry/settling."""

    stage: EventStage = EventStage.INGESTION
    kind: EventKind = EventKind.INGESTION_DEFERRED
    severity: EventSeverity = EventSeverity.WARNING
    payload: Mapping[str, Any] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class IngestionFailed(BaseEvent):
    """Event emitted for terminal ingestion failures."""

    stage: EventStage = EventStage.INGESTION
    kind: EventKind = EventKind.INGESTION_FAILED
    severity: EventSeverity = EventSeverity.ERROR
    payload: Mapping[str, Any] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class SyncTriggered(BaseEvent):
    """Event emitted when sync is requested or started."""

    stage: EventStage = EventStage.SYNC
    kind: EventKind = EventKind.SYNC_TRIGGERED
    severity: EventSeverity = EventSeverity.INFO
    payload: Mapping[str, Any] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class StartupFailed(BaseEvent):
    """Event emitted when startup bootstrap fails."""

    stage: EventStage = EventStage.STARTUP
    kind: EventKind = EventKind.STARTUP_FAILED
    severity: EventSeverity = EventSeverity.ERROR
    payload: Mapping[str, Any] = MappingProxyType({})


def _extract_correlation_context(
    context: RuntimeContext | ProcessingContext,
) -> tuple[str, str]:
    if isinstance(context, RuntimeContext | ProcessingContext):
        return context.event_id, context.trace_id
    raise EventValidationError("context must be RuntimeContext or ProcessingContext")


def _extract_occurred_at(outcome: Mapping[str, Any]) -> datetime:
    occurred_at = outcome.get("occurred_at")
    if occurred_at is None:
        return datetime.now(tz=UTC)
    if not isinstance(occurred_at, datetime):
        raise EventValidationError("outcome.occurred_at must be datetime when provided")
    return occurred_at


def event_from_outcome(
    outcome: Mapping[str, Any],
    context: RuntimeContext | ProcessingContext,
) -> BaseEvent:
    """Map normalized stage outcomes to canonical event contract models."""
    if not isinstance(outcome, Mapping):
        raise UnsupportedOutcomeError("outcome must be a mapping")
    status = outcome.get("status")
    if not isinstance(status, str):
        raise UnsupportedOutcomeError("outcome.status must be a string")

    event_id, trace_id = _extract_correlation_context(context)
    occurred_at = _extract_occurred_at(outcome)
    normalized_status = status.strip().lower()

    if normalized_status == "succeeded":
        payload: dict[str, Any] = {}
        if "candidate_id" in outcome:
            payload["candidate_id"] = outcome["candidate_id"]
        return IngestionSucceeded(
            event_id=event_id,
            trace_id=trace_id,
            occurred_at=occurred_at,
            payload=payload,
        )
    if normalized_status == "failed":
        return IngestionFailed(
            event_id=event_id,
            trace_id=trace_id,
            occurred_at=occurred_at,
            payload={"reason_code": outcome.get("reason_code", "unknown_failure")},
        )
    if normalized_status in {"deferred_retry", "deferred_stage"}:
        return IngestionDeferred(
            event_id=event_id,
            trace_id=trace_id,
            occurred_at=occurred_at,
            payload={
                "reason_code": outcome.get("reason_code", normalized_status),
            },
        )
    if normalized_status == "sync_triggered":
        payload = {}
        if "record_id" in outcome:
            payload["record_id"] = outcome["record_id"]
        return SyncTriggered(
            event_id=event_id,
            trace_id=trace_id,
            occurred_at=occurred_at,
            payload=payload,
        )
    if normalized_status == "startup_failed":
        return StartupFailed(
            event_id=event_id,
            trace_id=trace_id,
            occurred_at=occurred_at,
            payload={"reason_code": outcome.get("reason_code", "startup_failed")},
        )
    raise UnsupportedOutcomeError(f"unsupported outcome status: {status}")


def to_payload(event: BaseEvent) -> dict[str, Any]:
    """Serialize a contract event into transport-safe payload shape."""
    if not isinstance(event, BaseEvent):
        raise EventContractError("event must be a BaseEvent")
    return {
        "event_id": event.event_id,
        "trace_id": event.trace_id,
        "occurred_at": event.occurred_at.isoformat(),
        "stage": event.stage.value,
        "kind": event.kind.value,
        "severity": event.severity.value,
        "payload": _normalize_primitive(dict(event.payload)),
    }
