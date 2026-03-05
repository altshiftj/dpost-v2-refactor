from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Generic, Mapping, TypeVar

StateT = TypeVar("StateT")


class PipelineTerminalOutcome(StrEnum):
    """Terminal outcomes supported by the ingestion stage pipeline."""

    COMPLETED = "completed"
    DEFERRED_STAGE = "deferred_stage"
    RETRY = "retry"
    REJECTED = "rejected"
    FAILED = "failed"


class PipelineError(RuntimeError):
    """Base pipeline orchestration error."""


class PipelineMissingStageError(PipelineError):
    """Raised when no stage handler exists for the current stage id."""

    def __init__(self, stage_id: str) -> None:
        super().__init__(f"Missing stage handler for stage '{stage_id}'.")
        self.stage_id = stage_id


class PipelineTransitionError(PipelineError):
    """Raised when a stage emits a transition not allowed by policy."""

    def __init__(self, stage_id: str, message: str) -> None:
        super().__init__(f"Invalid transition from stage '{stage_id}': {message}")
        self.stage_id = stage_id


class PipelineCycleGuardError(PipelineError):
    """Raised when a run exceeds the configured max step count."""

    def __init__(self, max_steps: int) -> None:
        super().__init__(f"Pipeline exceeded max step guard ({max_steps}).")
        self.max_steps = max_steps


@dataclass(frozen=True, slots=True)
class PipelineTransitionPolicy:
    """Allowed transition targets for one stage id."""

    allowed_next_stages: frozenset[str]
    allowed_terminal_outcomes: frozenset[PipelineTerminalOutcome]


@dataclass(frozen=True, slots=True)
class StageDirective(Generic[StateT]):
    """Directive emitted by a stage handler."""

    kind: str
    next_stage: str | None = None
    outcome: PipelineTerminalOutcome | None = None
    state: StateT | None = None

    @classmethod
    def continue_to(
        cls,
        next_stage: str,
        state: StateT | None = None,
    ) -> StageDirective[StateT]:
        """Build a continue directive to the next stage id."""
        if not next_stage:
            raise ValueError("Continue directives require a non-empty next_stage.")
        return cls(kind="continue", next_stage=next_stage, state=state)

    @classmethod
    def terminal(
        cls,
        outcome: PipelineTerminalOutcome,
        state: StateT | None = None,
    ) -> StageDirective[StateT]:
        """Build a terminal directive with the final pipeline outcome."""
        return cls(kind="terminal", outcome=outcome, state=state)


@dataclass(frozen=True, slots=True)
class PipelineTransitionRecord:
    """One recorded stage transition emitted during a run."""

    stage_id: str
    directive: str
    next_stage: str | None = None
    outcome: PipelineTerminalOutcome | None = None


@dataclass(frozen=True, slots=True)
class PipelineRunResult(Generic[StateT]):
    """Terminal output of a pipeline run."""

    outcome: PipelineTerminalOutcome
    final_stage_id: str | None
    state: StateT
    transition_log: tuple[PipelineTransitionRecord, ...]


StageHandler = Callable[[StateT], StageDirective[StateT]]


@dataclass(slots=True)
class PipelineRunner(Generic[StateT]):
    """Pure stage orchestrator with explicit transition-table enforcement."""

    start_stage: str
    transition_table: Mapping[str, PipelineTransitionPolicy]
    max_steps: int = 50

    def run(
        self,
        *,
        initial_state: StateT,
        stage_handlers: Mapping[str, StageHandler[StateT]],
        cancellation_signal: Callable[[], bool] | None = None,
        cancellation_outcome: PipelineTerminalOutcome = PipelineTerminalOutcome.FAILED,
    ) -> PipelineRunResult[StateT]:
        """Execute stage handlers until a validated terminal directive is produced."""
        if self.max_steps <= 0:
            raise ValueError("max_steps must be greater than 0.")

        current_stage = self.start_stage
        state = initial_state
        transition_log: list[PipelineTransitionRecord] = []
        steps = 0
        last_stage_id: str | None = None
        should_cancel = cancellation_signal or (lambda: False)

        while True:
            if should_cancel():
                return PipelineRunResult(
                    outcome=cancellation_outcome,
                    final_stage_id=last_stage_id,
                    state=state,
                    transition_log=tuple(transition_log),
                )

            if steps >= self.max_steps:
                raise PipelineCycleGuardError(self.max_steps)

            policy = self.transition_table.get(current_stage)
            if policy is None:
                raise PipelineTransitionError(
                    current_stage,
                    "missing transition policy for current stage",
                )

            stage_handler = stage_handlers.get(current_stage)
            if stage_handler is None:
                raise PipelineMissingStageError(current_stage)

            directive = stage_handler(state)
            if directive.state is not None:
                state = directive.state

            steps += 1
            last_stage_id = current_stage

            if directive.kind == "continue":
                next_stage = directive.next_stage
                if next_stage is None:
                    raise PipelineTransitionError(
                        current_stage,
                        "continue directive must include next stage",
                    )
                if next_stage not in policy.allowed_next_stages:
                    raise PipelineTransitionError(
                        current_stage,
                        f"next stage '{next_stage}' is not allowed by transition table",
                    )
                transition_log.append(
                    PipelineTransitionRecord(
                        stage_id=current_stage,
                        directive="continue",
                        next_stage=next_stage,
                    )
                )
                current_stage = next_stage
                continue

            if directive.kind == "terminal":
                outcome = directive.outcome
                if outcome is None:
                    raise PipelineTransitionError(
                        current_stage,
                        "terminal directive must include terminal outcome",
                    )
                if outcome not in policy.allowed_terminal_outcomes:
                    raise PipelineTransitionError(
                        current_stage,
                        f"terminal outcome '{outcome.value}' is not allowed by transition table",
                    )
                transition_log.append(
                    PipelineTransitionRecord(
                        stage_id=current_stage,
                        directive="terminal",
                        outcome=outcome,
                    )
                )
                return PipelineRunResult(
                    outcome=outcome,
                    final_stage_id=current_stage,
                    state=state,
                    transition_log=tuple(transition_log),
                )

            raise PipelineTransitionError(
                current_stage,
                f"unknown stage directive '{directive.kind}'",
            )


DEFAULT_INGESTION_TRANSITION_TABLE: dict[str, PipelineTransitionPolicy] = {
    "resolve": PipelineTransitionPolicy(
        allowed_next_stages=frozenset({"stabilize"}),
        allowed_terminal_outcomes=frozenset(
            {PipelineTerminalOutcome.REJECTED, PipelineTerminalOutcome.FAILED}
        ),
    ),
    "stabilize": PipelineTransitionPolicy(
        allowed_next_stages=frozenset({"transform"}),
        allowed_terminal_outcomes=frozenset(
            {
                PipelineTerminalOutcome.RETRY,
                PipelineTerminalOutcome.REJECTED,
                PipelineTerminalOutcome.FAILED,
            }
        ),
    ),
    "transform": PipelineTransitionPolicy(
        allowed_next_stages=frozenset({"route"}),
        allowed_terminal_outcomes=frozenset(
            {
                PipelineTerminalOutcome.DEFERRED_STAGE,
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
