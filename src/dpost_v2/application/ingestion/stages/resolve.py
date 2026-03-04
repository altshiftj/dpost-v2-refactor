from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Mapping

from dpost_v2.application.ingestion.models.candidate import Candidate
from dpost_v2.application.ingestion.processor_factory import (
    ProcessorAmbiguousMatchError,
    ProcessorNotFoundError,
    ProcessorSelection,
)
from dpost_v2.application.ingestion.stages.pipeline import (
    PipelineTerminalOutcome,
    StageDirective,
)
from dpost_v2.application.ingestion.state import IngestionState


def run_resolve_stage(
    state: IngestionState,
    *,
    fs_facts_provider: Callable[[str], Mapping[str, Any]],
    processor_selector: Callable[[Candidate], ProcessorSelection],
) -> StageDirective[IngestionState]:
    """Resolve candidate metadata and processor selection for ingestion pipeline."""
    path = str(state.event.get("path", ""))
    fs_facts = fs_facts_provider(path)
    candidate = Candidate.from_event(state.event, fs_facts)

    try:
        selection = processor_selector(candidate)
    except ProcessorNotFoundError:
        rejected = state.with_updates(
            diagnostics={"resolve": {"reason_code": "processor_not_found"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.REJECTED, rejected)
    except ProcessorAmbiguousMatchError:
        failed = state.with_updates(
            diagnostics={"resolve": {"reason_code": "processor_ambiguous"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)

    resolved_candidate = candidate.with_resolution(
        plugin_id=selection.descriptor.plugin_id,
        processor_key=selection.descriptor.processor_key,
    )
    next_state = replace(
        state,
        candidate=resolved_candidate,
        processor=selection.processor,
        diagnostics={
            **dict(state.diagnostics),
            "resolve": {
                "plugin_id": selection.descriptor.plugin_id,
                "capability_reason": selection.descriptor.capability_reason,
                "cache_hit": selection.descriptor.cache_hit,
            },
        },
    )
    return StageDirective.continue_to("stabilize", next_state)
