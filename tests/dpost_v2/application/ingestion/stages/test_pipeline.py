from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

from dpost_v2.application.ingestion.stages.pipeline import (
    PipelineCycleGuardError,
    PipelineMissingStageError,
    PipelineRunner,
    PipelineTerminalOutcome,
    PipelineTransitionError,
    PipelineTransitionPolicy,
    StageDirective,
)


@dataclass(frozen=True)
class DemoState:
    steps: tuple[str, ...] = ()


def _with_step(state: DemoState, stage_id: str) -> DemoState:
    return replace(state, steps=(*state.steps, stage_id))


def _default_transition_table() -> dict[str, PipelineTransitionPolicy]:
    return {
        "resolve": PipelineTransitionPolicy(
            allowed_next_stages=frozenset({"stabilize"}),
            allowed_terminal_outcomes=frozenset(
                {PipelineTerminalOutcome.REJECTED, PipelineTerminalOutcome.FAILED}
            ),
        ),
        "stabilize": PipelineTransitionPolicy(
            allowed_next_stages=frozenset({"route"}),
            allowed_terminal_outcomes=frozenset(
                {
                    PipelineTerminalOutcome.RETRY,
                    PipelineTerminalOutcome.REJECTED,
                    PipelineTerminalOutcome.FAILED,
                }
            ),
        ),
        "route": PipelineTransitionPolicy(
            allowed_next_stages=frozenset({"persist"}),
            allowed_terminal_outcomes=frozenset(
                {PipelineTerminalOutcome.REJECTED, PipelineTerminalOutcome.FAILED}
            ),
        ),
        "persist": PipelineTransitionPolicy(
            allowed_next_stages=frozenset({"post_persist"}),
            allowed_terminal_outcomes=frozenset(
                {
                    PipelineTerminalOutcome.RETRY,
                    PipelineTerminalOutcome.REJECTED,
                    PipelineTerminalOutcome.FAILED,
                }
            ),
        ),
        "post_persist": PipelineTransitionPolicy(
            allowed_next_stages=frozenset(),
            allowed_terminal_outcomes=frozenset(
                {PipelineTerminalOutcome.COMPLETED, PipelineTerminalOutcome.FAILED}
            ),
        ),
    }


def test_pipeline_runner_sequences_stages_and_records_transition_log() -> None:
    runner = PipelineRunner(
        start_stage="resolve",
        transition_table=_default_transition_table(),
    )

    handlers = {
        "resolve": lambda state: StageDirective.continue_to(
            "stabilize", _with_step(state, "resolve")
        ),
        "stabilize": lambda state: StageDirective.continue_to(
            "route", _with_step(state, "stabilize")
        ),
        "route": lambda state: StageDirective.continue_to(
            "persist", _with_step(state, "route")
        ),
        "persist": lambda state: StageDirective.continue_to(
            "post_persist", _with_step(state, "persist")
        ),
        "post_persist": lambda state: StageDirective.terminal(
            PipelineTerminalOutcome.COMPLETED,
            _with_step(state, "post_persist"),
        ),
    }

    result = runner.run(initial_state=DemoState(), stage_handlers=handlers)

    assert result.outcome is PipelineTerminalOutcome.COMPLETED
    assert result.final_stage_id == "post_persist"
    assert result.state.steps == (
        "resolve",
        "stabilize",
        "route",
        "persist",
        "post_persist",
    )
    assert [entry.stage_id for entry in result.transition_log] == [
        "resolve",
        "stabilize",
        "route",
        "persist",
        "post_persist",
    ]


def test_pipeline_runner_raises_for_missing_stage_handler() -> None:
    runner = PipelineRunner(
        start_stage="resolve",
        transition_table=_default_transition_table(),
    )

    handlers = {
        "resolve": lambda state: StageDirective.continue_to(
            "stabilize", _with_step(state, "resolve")
        ),
        "stabilize": lambda state: StageDirective.continue_to(
            "route", _with_step(state, "stabilize")
        ),
    }

    with pytest.raises(PipelineMissingStageError, match="route"):
        runner.run(initial_state=DemoState(), stage_handlers=handlers)


def test_pipeline_runner_enforces_transition_table_for_next_stage() -> None:
    runner = PipelineRunner(
        start_stage="resolve",
        transition_table=_default_transition_table(),
    )

    handlers = {
        "resolve": lambda state: StageDirective.continue_to(
            "persist", _with_step(state, "resolve")
        ),
    }

    with pytest.raises(PipelineTransitionError, match="resolve"):
        runner.run(initial_state=DemoState(), stage_handlers=handlers)


def test_pipeline_runner_enforces_transition_table_for_terminal_outcome() -> None:
    runner = PipelineRunner(
        start_stage="resolve",
        transition_table=_default_transition_table(),
    )

    handlers = {
        "resolve": lambda state: StageDirective.continue_to(
            "stabilize", _with_step(state, "resolve")
        ),
        "stabilize": lambda state: StageDirective.continue_to(
            "route", _with_step(state, "stabilize")
        ),
        "route": lambda state: StageDirective.terminal(
            PipelineTerminalOutcome.COMPLETED,
            _with_step(state, "route"),
        ),
    }

    with pytest.raises(PipelineTransitionError, match="terminal"):
        runner.run(initial_state=DemoState(), stage_handlers=handlers)


def test_pipeline_runner_raises_when_cycle_guard_is_exceeded() -> None:
    transition_table = {
        "resolve": PipelineTransitionPolicy(
            allowed_next_stages=frozenset({"stabilize"}),
            allowed_terminal_outcomes=frozenset(),
        ),
        "stabilize": PipelineTransitionPolicy(
            allowed_next_stages=frozenset({"resolve"}),
            allowed_terminal_outcomes=frozenset(),
        ),
    }

    runner = PipelineRunner(
        start_stage="resolve",
        transition_table=transition_table,
        max_steps=3,
    )

    handlers = {
        "resolve": lambda state: StageDirective.continue_to(
            "stabilize", _with_step(state, "resolve")
        ),
        "stabilize": lambda state: StageDirective.continue_to(
            "resolve", _with_step(state, "stabilize")
        ),
    }

    with pytest.raises(PipelineCycleGuardError):
        runner.run(initial_state=DemoState(), stage_handlers=handlers)


def test_pipeline_runner_returns_cancellation_terminal_outcome() -> None:
    runner = PipelineRunner(
        start_stage="resolve",
        transition_table=_default_transition_table(),
    )

    cancellation_requested = {"value": False}

    def resolve_handler(state: DemoState) -> StageDirective[DemoState]:
        cancellation_requested["value"] = True
        return StageDirective.continue_to("stabilize", _with_step(state, "resolve"))

    handlers = {
        "resolve": resolve_handler,
        "stabilize": lambda state: StageDirective.continue_to(
            "route", _with_step(state, "stabilize")
        ),
    }

    result = runner.run(
        initial_state=DemoState(),
        stage_handlers=handlers,
        cancellation_signal=lambda: cancellation_requested["value"],
        cancellation_outcome=PipelineTerminalOutcome.RETRY,
    )

    assert result.outcome is PipelineTerminalOutcome.RETRY
    assert result.final_stage_id == "resolve"
    assert result.state.steps == ("resolve",)
    assert [entry.stage_id for entry in result.transition_log] == ["resolve"]
