from __future__ import annotations

from pathlib import PurePath
from typing import Callable

from dpost_v2.application.ingestion.models.candidate import Candidate
from dpost_v2.application.ingestion.policies.force_path import (
    ForcePathDecisionType,
    evaluate_force_path,
)
from dpost_v2.application.ingestion.stages.pipeline import (
    PipelineTerminalOutcome,
    StageDirective,
)
from dpost_v2.application.ingestion.state import IngestionState


def run_route_stage(
    state: IngestionState,
    *,
    allowed_roots: tuple[str, ...],
    route_selector: Callable[[Candidate], str | None],
    filename_builder: Callable[[IngestionState], str],
) -> StageDirective[IngestionState]:
    """Compute routed target path and enforce force-path policy constraints."""
    candidate = state.candidate
    if candidate is None:
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, state)

    route_root = route_selector(candidate)
    if not route_root:
        rejected = state.with_updates(
            diagnostics={"route": {"reason_code": "no_route_rule"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.REJECTED, rejected)

    filename = filename_builder(state)
    default_target = str(PurePath(route_root) / filename)
    decision = evaluate_force_path(
        override_path=state.event.get("force_path"),
        allowed_roots=allowed_roots,
        default_target=default_target,
    )
    if decision.decision_type is ForcePathDecisionType.REJECT_OVERRIDE:
        rejected = state.with_updates(
            diagnostics={"route": {"reason_code": decision.reason_code}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.REJECTED, rejected)

    if decision.normalized_path is None:
        failed = state.with_updates(
            diagnostics={"route": {"reason_code": "missing_target_path"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)

    routed = candidate.with_route(
        target_path=decision.normalized_path,
        route_tokens={
            "force_path_decision": decision.decision_type.value,
            "reason_code": decision.reason_code,
        },
    )
    next_state = state.with_updates(
        candidate=routed,
        diagnostics={
            "route": {
                "target_path": decision.normalized_path,
                "reason_code": decision.reason_code,
            }
        },
    )
    return StageDirective.continue_to("persist", next_state)
