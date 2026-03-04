from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Generic, Mapping, Protocol, TypeVar

from dpost_v2.application.ingestion.stages.pipeline import (
    PipelineRunResult,
    PipelineTerminalOutcome,
    PipelineTransitionRecord,
)


StateT = TypeVar("StateT")


class IngestionOutcomeKind(StrEnum):
    """Top-level terminal outcome returned by the ingestion engine."""

    SUCCEEDED = "succeeded"
    DEFERRED_RETRY = "deferred_retry"
    REJECTED = "rejected"
    FAILED_TERMINAL = "failed_terminal"


class FailureTerminalType(StrEnum):
    """Normalized failure terminal types used by failure outcome policy."""

    RETRY = "retry"
    REJECTED = "rejected"
    FAILED = "failed"


class IngestionEngineError(RuntimeError):
    """Base engine-level error type."""


class IngestionEngineConfigurationError(IngestionEngineError):
    """Raised when engine dependencies violate required contracts."""


@dataclass(frozen=True, slots=True)
class FailureClassification:
    """Normalized exception classification emitted by error handling policy."""

    reason_code: str
    severity: str
    retryable: bool
    stage_id: str | None
    diagnostics: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class FailureOutcome:
    """Canonical failure outcome used for final engine mapping/emission."""

    terminal_type: FailureTerminalType
    stage_id: str | None
    reason_code: str
    severity: str
    retry_plan: Mapping[str, Any] | None
    should_emit: bool


@dataclass(frozen=True, slots=True)
class IngestionOutcome(Generic[StateT]):
    """Terminal ingestion engine result for one processed event."""

    kind: IngestionOutcomeKind
    final_stage_id: str | None
    state: StateT | None
    stage_trace: tuple[PipelineTransitionRecord, ...]
    retry_plan: Mapping[str, Any] | None
    emission_status: str


class PipelineRunnerPort(Protocol[StateT]):
    """Protocol for the stage pipeline runner consumed by the engine."""

    def run(self, **kwargs: Any) -> PipelineRunResult[StateT]:
        """Run a staged pipeline and return one terminal result."""


ErrorHandlingPolicy = Callable[[Exception, str | None], FailureClassification]
FailureOutcomePolicy = Callable[[FailureClassification], FailureOutcome]
FailureEmitter = Callable[[FailureOutcome, Mapping[str, Any]], None]


REQUIRED_STAGE_ORDER: tuple[str, ...] = (
    "resolve",
    "stabilize",
    "route",
    "persist",
    "post_persist",
)


@dataclass(slots=True)
class IngestionEngine(Generic[StateT]):
    """Ingestion orchestrator wrapping stage pipeline and failure policies."""

    pipeline_runner: PipelineRunnerPort[StateT]
    stage_handlers: Mapping[str, Callable[[StateT], Any]]
    error_handling_policy: ErrorHandlingPolicy | None = None
    failure_outcome_policy: FailureOutcomePolicy | None = None
    failure_emitter: FailureEmitter | None = None
    cancellation_signal: Callable[[], bool] | None = None

    def __post_init__(self) -> None:
        """Validate startup-time stage bindings and pipeline prerequisites."""
        missing = [stage for stage in REQUIRED_STAGE_ORDER if stage not in self.stage_handlers]
        if missing:
            joined = ", ".join(missing)
            raise IngestionEngineConfigurationError(
                f"Missing required stage handlers: {joined}"
            )

    def process(
        self,
        *,
        event: Mapping[str, Any],
        initial_state_factory: Callable[[Mapping[str, Any]], StateT] | None = None,
    ) -> IngestionOutcome[StateT]:
        """Run one ingestion event through pipeline and normalize terminal outcome."""
        state_factory = initial_state_factory or (lambda payload: payload)  # type: ignore[return-value]
        initial_state = state_factory(event)

        try:
            pipeline_result = self.pipeline_runner.run(
                initial_state=initial_state,
                stage_handlers=self.stage_handlers,
                cancellation_signal=self.cancellation_signal,
                cancellation_outcome=PipelineTerminalOutcome.FAILED,
            )
            return self._map_pipeline_result(pipeline_result)
        except Exception as exc:  # noqa: BLE001
            return self._normalize_exception(exc, event)

    @staticmethod
    def _map_pipeline_terminal(outcome: PipelineTerminalOutcome) -> IngestionOutcomeKind:
        if outcome is PipelineTerminalOutcome.COMPLETED:
            return IngestionOutcomeKind.SUCCEEDED
        if outcome is PipelineTerminalOutcome.RETRY:
            return IngestionOutcomeKind.DEFERRED_RETRY
        if outcome is PipelineTerminalOutcome.REJECTED:
            return IngestionOutcomeKind.REJECTED
        return IngestionOutcomeKind.FAILED_TERMINAL

    @staticmethod
    def _map_failure_terminal(terminal_type: FailureTerminalType) -> IngestionOutcomeKind:
        if terminal_type is FailureTerminalType.RETRY:
            return IngestionOutcomeKind.DEFERRED_RETRY
        if terminal_type is FailureTerminalType.REJECTED:
            return IngestionOutcomeKind.REJECTED
        return IngestionOutcomeKind.FAILED_TERMINAL

    def _map_pipeline_result(self, result: PipelineRunResult[StateT]) -> IngestionOutcome[StateT]:
        return IngestionOutcome(
            kind=self._map_pipeline_terminal(result.outcome),
            final_stage_id=result.final_stage_id,
            state=result.state,
            stage_trace=result.transition_log,
            retry_plan=None,
            emission_status="skipped",
        )

    def _normalize_exception(
        self,
        exc: Exception,
        event: Mapping[str, Any],
    ) -> IngestionOutcome[StateT]:
        stage_id = getattr(exc, "stage_id", None)
        classification = self._classify_exception(exc, stage_id)
        failure_outcome = self._build_failure_outcome(classification)
        emission_status = self._emit_failure_if_needed(failure_outcome, event)

        return IngestionOutcome(
            kind=self._map_failure_terminal(failure_outcome.terminal_type),
            final_stage_id=failure_outcome.stage_id,
            state=None,
            stage_trace=(),
            retry_plan=failure_outcome.retry_plan,
            emission_status=emission_status,
        )

    def _classify_exception(
        self,
        exc: Exception,
        stage_id: str | None,
    ) -> FailureClassification:
        if self.error_handling_policy is not None:
            return self.error_handling_policy(exc, stage_id)

        return FailureClassification(
            reason_code="ingestion_unhandled_exception",
            severity="error",
            retryable=False,
            stage_id=stage_id,
            diagnostics={"type": exc.__class__.__name__, "message": str(exc)},
        )

    def _build_failure_outcome(
        self,
        classification: FailureClassification,
    ) -> FailureOutcome:
        if self.failure_outcome_policy is not None:
            return self.failure_outcome_policy(classification)

        terminal_type = (
            FailureTerminalType.RETRY
            if classification.retryable
            else FailureTerminalType.FAILED
        )
        retry_plan: Mapping[str, Any] | None = None
        if terminal_type is FailureTerminalType.RETRY:
            retry_plan = {"delay_seconds": 0, "next_attempt": 1}

        return FailureOutcome(
            terminal_type=terminal_type,
            stage_id=classification.stage_id,
            reason_code=classification.reason_code,
            severity=classification.severity,
            retry_plan=retry_plan,
            should_emit=True,
        )

    def _emit_failure_if_needed(
        self,
        failure_outcome: FailureOutcome,
        event: Mapping[str, Any],
    ) -> str:
        if not failure_outcome.should_emit or self.failure_emitter is None:
            return "skipped"

        try:
            self.failure_emitter(failure_outcome, event)
            return "emitted"
        except Exception:  # noqa: BLE001
            return "failed"
