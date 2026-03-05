from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest

from dpost_v2.application.ingestion.engine import (
    FailureClassification,
    FailureOutcome,
    FailureTerminalType,
    IngestionEngine,
    IngestionEngineConfigurationError,
    IngestionOutcomeKind,
)
from dpost_v2.application.ingestion.stages.pipeline import (
    DEFAULT_INGESTION_TRANSITION_TABLE,
    PipelineRunner,
    PipelineTerminalOutcome,
    StageDirective,
)


@dataclass(frozen=True)
class DemoState:
    event: dict[str, Any]
    steps: tuple[str, ...] = ()


def _append_step(state: DemoState, stage_id: str) -> DemoState:
    return DemoState(event=state.event, steps=(*state.steps, stage_id))


def _terminal_handlers() -> dict[str, Any]:
    return {
        "resolve": lambda state: StageDirective.terminal(
            PipelineTerminalOutcome.COMPLETED,
            state,
        ),
        "stabilize": lambda state: StageDirective.terminal(
            PipelineTerminalOutcome.COMPLETED,
            state,
        ),
        "transform": lambda state: StageDirective.terminal(
            PipelineTerminalOutcome.COMPLETED,
            state,
        ),
        "route": lambda state: StageDirective.terminal(
            PipelineTerminalOutcome.COMPLETED,
            state,
        ),
        "persist": lambda state: StageDirective.terminal(
            PipelineTerminalOutcome.COMPLETED,
            state,
        ),
        "post_persist": lambda state: StageDirective.terminal(
            PipelineTerminalOutcome.COMPLETED,
            state,
        ),
    }


def test_engine_requires_all_required_stage_handlers() -> None:
    with pytest.raises(IngestionEngineConfigurationError, match="post_persist"):
        IngestionEngine(
            pipeline_runner=PipelineRunner(
                start_stage="resolve",
                transition_table=DEFAULT_INGESTION_TRANSITION_TABLE,
            ),
            stage_handlers={
                "resolve": lambda state: StageDirective.continue_to("stabilize", state),
                "stabilize": lambda state: StageDirective.continue_to(
                    "transform", state
                ),
                "transform": lambda state: StageDirective.continue_to(
                    "route", state
                ),
                "route": lambda state: StageDirective.continue_to("persist", state),
                "persist": lambda state: StageDirective.terminal(
                    PipelineTerminalOutcome.COMPLETED,
                    state,
                ),
            },
        )


def test_engine_maps_completed_pipeline_result_to_succeeded_outcome() -> None:
    handlers = {
        "resolve": lambda state: StageDirective.continue_to(
            "stabilize", _append_step(state, "resolve")
        ),
        "stabilize": lambda state: StageDirective.continue_to(
            "transform", _append_step(state, "stabilize")
        ),
        "transform": lambda state: StageDirective.continue_to(
            "route", _append_step(state, "transform")
        ),
        "route": lambda state: StageDirective.continue_to(
            "persist", _append_step(state, "route")
        ),
        "persist": lambda state: StageDirective.continue_to(
            "post_persist", _append_step(state, "persist")
        ),
        "post_persist": lambda state: StageDirective.terminal(
            PipelineTerminalOutcome.COMPLETED,
            _append_step(state, "post_persist"),
        ),
    }

    engine = IngestionEngine(
        pipeline_runner=PipelineRunner(
            start_stage="resolve",
            transition_table=DEFAULT_INGESTION_TRANSITION_TABLE,
        ),
        stage_handlers=handlers,
    )

    outcome = engine.process(
        event={"path": "input.csv"}, initial_state_factory=DemoState
    )

    assert outcome.kind is IngestionOutcomeKind.SUCCEEDED
    assert outcome.final_stage_id == "post_persist"
    assert outcome.state.steps == (
        "resolve",
        "stabilize",
        "transform",
        "route",
        "persist",
        "post_persist",
    )
    assert [entry.stage_id for entry in outcome.stage_trace] == [
        "resolve",
        "stabilize",
        "transform",
        "route",
        "persist",
        "post_persist",
    ]


class _ExplodingPipelineRunner:
    def run(self, **_: Any) -> Any:
        raise RuntimeError("boom")


class _RaisingEmitter:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, outcome: FailureOutcome, event: dict[str, Any]) -> None:
        self.calls += 1
        raise RuntimeError("emit failure")


def test_engine_normalizes_exceptions_and_returns_retry_outcome() -> None:
    emitter = _RaisingEmitter()

    engine = IngestionEngine(
        pipeline_runner=_ExplodingPipelineRunner(),
        stage_handlers=_terminal_handlers(),
        error_handling_policy=lambda exc, stage_id: FailureClassification(
            reason_code="unexpected",
            severity="error",
            retryable=True,
            stage_id=stage_id,
            diagnostics={"message": str(exc)},
        ),
        failure_outcome_policy=lambda classification: FailureOutcome(
            terminal_type=FailureTerminalType.RETRY,
            stage_id=classification.stage_id,
            reason_code=classification.reason_code,
            severity=classification.severity,
            retry_plan={"delay_seconds": 15, "next_attempt": 2},
            should_emit=True,
        ),
        failure_emitter=emitter,
    )

    outcome = engine.process(event={"path": "input.csv"})

    assert outcome.kind is IngestionOutcomeKind.DEFERRED_RETRY
    assert outcome.retry_plan == {"delay_seconds": 15, "next_attempt": 2}
    assert outcome.emission_status == "failed"
    assert emitter.calls == 1


def test_engine_maps_rejected_failure_outcome() -> None:
    engine = IngestionEngine(
        pipeline_runner=_ExplodingPipelineRunner(),
        stage_handlers=_terminal_handlers(),
        error_handling_policy=lambda exc, stage_id: FailureClassification(
            reason_code="validation",
            severity="warning",
            retryable=False,
            stage_id=stage_id,
            diagnostics={"message": str(exc)},
        ),
        failure_outcome_policy=lambda classification: FailureOutcome(
            terminal_type=FailureTerminalType.REJECTED,
            stage_id=classification.stage_id,
            reason_code=classification.reason_code,
            severity=classification.severity,
            retry_plan=None,
            should_emit=False,
        ),
    )

    outcome = engine.process(event={"path": "input.csv"})

    assert outcome.kind is IngestionOutcomeKind.REJECTED
    assert outcome.retry_plan is None
    assert outcome.emission_status == "skipped"


def test_engine_returns_failed_terminal_when_initial_state_factory_raises() -> None:
    engine = IngestionEngine(
        pipeline_runner=PipelineRunner(
            start_stage="resolve",
            transition_table=DEFAULT_INGESTION_TRANSITION_TABLE,
        ),
        stage_handlers=_terminal_handlers(),
    )

    def _raising_factory(_: Any) -> DemoState:
        raise ValueError("bad-initial-state")

    outcome = engine.process(
        event=cast(dict[str, Any], None),
        initial_state_factory=_raising_factory,
    )

    assert outcome.kind is IngestionOutcomeKind.FAILED_TERMINAL
    assert outcome.final_stage_id is None
    assert outcome.state is None
    assert outcome.retry_plan is None


def test_engine_returns_failed_terminal_when_error_policy_raises() -> None:
    engine = IngestionEngine(
        pipeline_runner=_ExplodingPipelineRunner(),
        stage_handlers=_terminal_handlers(),
        error_handling_policy=lambda exc, stage_id: (_ for _ in ()).throw(
            RuntimeError("classification_failed")
        ),
    )

    outcome = engine.process(event={"path": "input.csv"})

    assert outcome.kind is IngestionOutcomeKind.FAILED_TERMINAL
    assert outcome.retry_plan is None
    assert outcome.emission_status == "skipped"


def test_engine_returns_failed_terminal_when_failure_outcome_policy_raises() -> None:
    engine = IngestionEngine(
        pipeline_runner=_ExplodingPipelineRunner(),
        stage_handlers=_terminal_handlers(),
        error_handling_policy=lambda exc, stage_id: FailureClassification(
            reason_code="unexpected",
            severity="error",
            retryable=False,
            stage_id=stage_id,
            diagnostics={"message": str(exc)},
        ),
        failure_outcome_policy=lambda classification: (_ for _ in ()).throw(
            RuntimeError("failure_outcome_failed")
        ),
    )

    outcome = engine.process(event={"path": "input.csv"})

    assert outcome.kind is IngestionOutcomeKind.FAILED_TERMINAL
    assert outcome.retry_plan is None
    assert outcome.emission_status == "skipped"
