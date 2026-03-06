"""Top-level V2 runtime orchestration loop for ingestion processing."""

from __future__ import annotations

import inspect
import time
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext
from dpost_v2.application.contracts.events import event_from_outcome, to_payload
from dpost_v2.application.ingestion.engine import IngestionOutcomeKind
from dpost_v2.application.session.session_manager import SessionManager, TimeoutOutcome


@dataclass(frozen=True, slots=True)
class RunResult:
    """Deterministic summary of one runtime loop execution."""

    processed_count: int
    skipped_count: int
    failed_count: int
    terminal_reason: str


class DPostApp:
    """Runtime loop that coordinates session lifecycle and ingestion outcomes."""

    def __init__(
        self,
        *,
        session_manager: SessionManager,
        ingestion_engine: Any,
        event_source: Iterable[Mapping[str, Any]],
        event_emitter: Callable[[Mapping[str, Any]], None],
        clock: Any,
        session_id: str,
        trace_id: str,
        mode: str = "headless",
        profile: str = "default",
        dependency_ids: Mapping[str, str] | None = None,
        settings_snapshot: Mapping[str, Any] | None = None,
        cancellation_signal: Callable[[], bool] | None = None,
        stop_on_failure: bool = True,
        loop_mode: str = "oneshot",
        poll_interval_seconds: float = 1.0,
        idle_wait: Callable[[float], None] | None = None,
        shutdown_hook: Callable[[], None] | None = None,
    ) -> None:
        self._session_manager = session_manager
        self._ingestion_engine = ingestion_engine
        self._event_source = event_source
        self._event_emitter = event_emitter
        self._clock = clock
        self._session_id = str(session_id)
        self._trace_id = str(trace_id)
        self._mode = str(mode)
        self._profile = str(profile)
        self._dependency_ids = dict(
            dependency_ids
            or {
                "clock": "clock-default",
                "ui": "ui-default",
                "sync": "sync-default",
            }
        )
        self._settings_snapshot = dict(settings_snapshot or {})
        self._cancellation_signal = cancellation_signal or (lambda: False)
        self._stop_on_failure = stop_on_failure
        normalized_loop_mode = str(loop_mode).strip().lower() or "oneshot"
        if normalized_loop_mode not in {"oneshot", "continuous"}:
            raise ValueError("loop_mode must be 'oneshot' or 'continuous'")
        self._loop_mode = normalized_loop_mode
        self._poll_interval_seconds = float(poll_interval_seconds)
        if self._poll_interval_seconds < 0:
            raise ValueError("poll_interval_seconds must be >= 0")
        self._idle_wait = idle_wait or _resolve_idle_wait(clock)
        self._shutdown_hook = shutdown_hook
        self._shutdown_completed = False
        self._seen_event_ids: set[str] = set()
        self._engine_accepts_processing_context = _accepts_processing_context(
            self._ingestion_engine.process
        )
        self._runtime_context = self._build_runtime_context()
        self._event_source_consumed = False

    def run(self) -> RunResult:
        """Run ingestion loop from event source until completion, cancellation, or failure."""
        processed_count = 0
        skipped_count = 0
        failed_count = 0
        terminal_reason = "end_of_stream"

        self._session_manager.start_session(session_id=self._session_id)
        self._emit("runtime_started")

        try:
            while True:
                timeout_state = self._session_manager.evaluate_timeouts()
                if timeout_state.outcome is TimeoutOutcome.HARD_TIMEOUT:
                    terminal_reason = "hard_timeout"
                    break
                if timeout_state.outcome is TimeoutOutcome.SOFT_TIMEOUT:
                    terminal_reason = "soft_timeout"
                    break

                batch = self._next_event_batch()
                if not batch:
                    if self._cancellation_signal():
                        terminal_reason = "cancelled"
                        break
                    if self._loop_mode == "oneshot":
                        terminal_reason = "end_of_stream"
                        break
                    self._idle_wait(self._poll_interval_seconds)
                    continue

                (
                    batch_processed_count,
                    batch_skipped_count,
                    batch_failed_count,
                    batch_terminal_reason,
                ) = self._process_event_batch(batch)
                processed_count += batch_processed_count
                skipped_count += batch_skipped_count
                failed_count += batch_failed_count
                if batch_terminal_reason is not None:
                    terminal_reason = batch_terminal_reason
                    break
                if self._loop_mode == "oneshot":
                    terminal_reason = "end_of_stream"
                    break
        except Exception:
            self._session_manager.abort_session(
                session_id=self._session_id,
                reason_code="runtime_exception",
            )
            self._emit("runtime_failed", reason_code="runtime_exception")
            raise

        if terminal_reason in {"failed_terminal", "hard_timeout"}:
            self._session_manager.abort_session(
                session_id=self._session_id,
                reason_code=terminal_reason,
            )
            self._emit("runtime_failed", reason_code=terminal_reason)
        elif terminal_reason == "cancelled":
            self._session_manager.abort_session(
                session_id=self._session_id,
                reason_code=terminal_reason,
            )
            self._emit("runtime_cancelled", reason_code=terminal_reason)
        else:
            self._session_manager.stop_session(session_id=self._session_id)
            self._emit("runtime_completed", reason_code=terminal_reason)

        return RunResult(
            processed_count=processed_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            terminal_reason=terminal_reason,
        )

    def shutdown(self) -> None:
        """Release runtime-owned adapters exactly once per app instance."""
        if self._shutdown_completed:
            return
        self._shutdown_completed = True
        if self._shutdown_hook is not None:
            self._shutdown_hook()

    def _next_event_batch(self) -> tuple[Mapping[str, Any], ...]:
        if callable(self._event_source):
            source = self._event_source()
            if source is None:
                return ()
            return tuple(source)

        if self._event_source_consumed:
            return ()
        self._event_source_consumed = True
        return tuple(self._event_source)

    def _process_event_batch(
        self,
        batch: Iterable[Mapping[str, Any]],
    ) -> tuple[int, int, int, str | None]:
        processed_count = 0
        skipped_count = 0
        failed_count = 0

        for event in batch:
            timeout_state = self._session_manager.evaluate_timeouts()
            if timeout_state.outcome is TimeoutOutcome.HARD_TIMEOUT:
                return processed_count, skipped_count, failed_count, "hard_timeout"
            if timeout_state.outcome is TimeoutOutcome.SOFT_TIMEOUT:
                return processed_count, skipped_count, failed_count, "soft_timeout"

            if self._cancellation_signal():
                return processed_count, skipped_count, failed_count, "cancelled"

            event_id = _extract_event_id(event)
            if event_id in self._seen_event_ids:
                skipped_count += 1
                self._emit(
                    "runtime_event_skipped",
                    event_id=event_id,
                    reason_code="duplicate_event_id",
                )
                continue
            self._seen_event_ids.add(event_id)

            processing_context = self._build_processing_context(
                event, event_id=event_id
            )
            self._session_manager.record_activity(session_id=self._session_id)
            outcome = self._process_event(
                event=event,
                processing_context=processing_context,
            )
            processed_count += 1

            self._emit(
                "runtime_event_processed",
                event_id=event_id,
                outcome_kind=str(outcome.kind),
            )
            self._emit_canonical_outcome_event(
                outcome_kind=outcome.kind,
                processing_context=processing_context,
            )

            if outcome.kind in {
                IngestionOutcomeKind.REJECTED,
                IngestionOutcomeKind.FAILED_TERMINAL,
            }:
                failed_count += 1
                if self._stop_on_failure:
                    return (
                        processed_count,
                        skipped_count,
                        failed_count,
                        "failed_terminal",
                    )

        return processed_count, skipped_count, failed_count, None

    def _emit(self, kind: str, **extra_payload: Any) -> None:
        payload: dict[str, Any] = {
            "kind": kind,
            "session_id": self._session_id,
            "trace_id": self._trace_id,
            "occurred_at": _as_isoformat(self._clock.now()),
        }
        payload.update(extra_payload)
        self._event_emitter(MappingProxyType(payload))

    def _build_runtime_context(self) -> RuntimeContext:
        settings_payload = {
            "mode": self._mode,
            "profile": self._profile,
            "session_id": self._session_id,
            "event_id": f"{self._trace_id}:runtime",
            "trace_id": self._trace_id,
        }
        settings_payload.update(self._settings_snapshot)
        return RuntimeContext.from_settings(
            settings=settings_payload,
            dependency_ids=self._dependency_ids,
        )

    def _build_processing_context(
        self,
        event: Mapping[str, Any],
        *,
        event_id: str,
    ) -> ProcessingContext:
        source_path = event.get("path", event.get("source_path"))
        if not isinstance(source_path, str) or not source_path.strip():
            raise ValueError(
                "runtime event must include non-empty 'path' or 'source_path'"
            )

        observed_at = event.get("observed_at", self._clock.now())
        if not isinstance(observed_at, datetime):
            raise ValueError(
                "runtime event 'observed_at' must be datetime when provided"
            )

        event_type_value = event.get("event_type", event.get("event_kind", "created"))
        if not isinstance(event_type_value, str) or not event_type_value.strip():
            raise ValueError("runtime event must include non-empty event type")

        return ProcessingContext.for_candidate(
            self._runtime_context,
            {
                "source_path": source_path,
                "event_type": event_type_value,
                "observed_at": observed_at,
                "event_id": event_id,
                "trace_id": self._trace_id,
            },
        )

    def _process_event(
        self,
        *,
        event: Mapping[str, Any],
        processing_context: ProcessingContext,
    ) -> Any:
        if self._engine_accepts_processing_context:
            return self._ingestion_engine.process(
                event=event,
                processing_context=processing_context,
            )
        return self._ingestion_engine.process(event=event)

    def _emit_canonical_outcome_event(
        self,
        *,
        outcome_kind: IngestionOutcomeKind,
        processing_context: ProcessingContext,
    ) -> None:
        payload = _outcome_payload(outcome_kind, processing_context=processing_context)
        contract_event = event_from_outcome(payload, processing_context)
        self._event_emitter(MappingProxyType(to_payload(contract_event)))


def _extract_event_id(event: Mapping[str, Any]) -> str:
    raw_value = event.get("event_id")
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError("event_id must be a non-empty string in runtime event payload")
    return raw_value.strip()


def _as_isoformat(value: datetime) -> str:
    if not isinstance(value, datetime):
        raise ValueError("clock.now() must return datetime")
    return value.isoformat()


def _outcome_payload(
    outcome_kind: IngestionOutcomeKind,
    *,
    processing_context: ProcessingContext,
) -> Mapping[str, Any]:
    if outcome_kind is IngestionOutcomeKind.SUCCEEDED:
        return {
            "status": "succeeded",
            "candidate_id": processing_context.event_id,
        }
    if outcome_kind is IngestionOutcomeKind.DEFERRED_STAGE:
        return {"status": "deferred_stage", "reason_code": "deferred_stage"}
    if outcome_kind is IngestionOutcomeKind.DEFERRED_RETRY:
        return {"status": "deferred_retry", "reason_code": "deferred_retry"}
    if outcome_kind is IngestionOutcomeKind.REJECTED:
        return {"status": "failed", "reason_code": "rejected"}
    return {"status": "failed", "reason_code": "failed_terminal"}


def _accepts_processing_context(method: Callable[..., Any]) -> bool:
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        return False
    return "processing_context" in signature.parameters


def _resolve_idle_wait(clock: object) -> Callable[[float], None]:
    candidate = getattr(clock, "sleep", None)
    if callable(candidate):
        return candidate
    return time.sleep
