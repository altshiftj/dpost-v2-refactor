from __future__ import annotations

from dataclasses import dataclass

from dpost_v2.application.ingestion.models.candidate import Candidate
from dpost_v2.application.ingestion.processor_factory import (
    ProcessorSelection,
    SelectionDescriptor,
)
from dpost_v2.application.ingestion.stages.pipeline import PipelineTerminalOutcome
from dpost_v2.application.ingestion.stages.resolve import run_resolve_stage
from dpost_v2.application.ingestion.stages.route import run_route_stage
from dpost_v2.application.ingestion.stages.stabilize import run_stabilize_stage
from dpost_v2.application.ingestion.state import IngestionState


class _Processor:
    def process(self) -> None:
        return None


@dataclass
class _GateResult:
    decision: str
    reason_code: str


def _state() -> IngestionState:
    return IngestionState(
        event={
            "path": "incoming/file.txt",
            "event_kind": "created",
            "observed_at": 100.0,
        }
    )


def test_resolve_stage_continues_to_stabilize_on_success() -> None:
    directive = run_resolve_stage(
        _state(),
        fs_facts_provider=lambda path: {"size": 1, "modified_at": 95.0},
        processor_selector=lambda candidate: ProcessorSelection(
            processor=_Processor(),
            descriptor=SelectionDescriptor(
                plugin_id="plug",
                processor_key="proc",
                capability_reason="ok",
                cache_hit=False,
            ),
        ),
    )

    assert directive.kind == "continue"
    assert directive.next_stage == "stabilize"
    assert directive.state.candidate is not None


def test_stabilize_stage_returns_retry_for_unstable_candidate() -> None:
    candidate = Candidate.from_event(
        {"path": "incoming/file.txt", "event_kind": "created", "observed_at": 100.0},
        {"modified_at": 99.0},
    ).with_resolution("plug", "proc")
    state = IngestionState(event={}, candidate=candidate)

    directive = run_stabilize_stage(
        state,
        modified_event_gate=lambda key, ts: _GateResult("allow", "ok"),
        now_provider=lambda: 100.0,
        settle_delay_seconds=5.0,
    )

    assert directive.kind == "terminal"
    assert directive.outcome is PipelineTerminalOutcome.RETRY


def test_route_stage_rejects_unsafe_force_path() -> None:
    candidate = Candidate.from_event(
        {"path": "incoming/file.txt", "event_kind": "created", "observed_at": 100.0},
        {"modified_at": 90.0},
    ).with_resolution("plug", "proc")
    state = IngestionState(
        event={"force_path": "C:/other/out.txt"}, candidate=candidate
    )

    directive = run_route_stage(
        state,
        allowed_roots=("C:/dest",),
        route_selector=lambda c: "C:/dest",
        filename_builder=lambda c: "out.txt",
    )

    assert directive.kind == "terminal"
    assert directive.outcome is PipelineTerminalOutcome.REJECTED


def test_route_stage_continues_to_persist_when_target_is_valid() -> None:
    candidate = Candidate.from_event(
        {"path": "incoming/file.txt", "event_kind": "created", "observed_at": 100.0},
        {"modified_at": 90.0},
    ).with_resolution("plug", "proc")
    state = IngestionState(event={}, candidate=candidate)

    directive = run_route_stage(
        state,
        allowed_roots=("C:/dest",),
        route_selector=lambda c: "C:/dest",
        filename_builder=lambda c: "out.txt",
    )

    assert directive.kind == "continue"
    assert directive.next_stage == "persist"
    assert directive.state.candidate is not None
    assert directive.state.candidate.target_path == "C:/dest/out.txt"
