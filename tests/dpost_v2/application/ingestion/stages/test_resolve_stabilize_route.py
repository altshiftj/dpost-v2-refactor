from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext
from dpost_v2.application.contracts.plugin_contracts import ProcessorResult
from dpost_v2.application.ingestion.models.candidate import Candidate
from dpost_v2.application.ingestion.processor_factory import (
    ProcessorSelection,
    SelectionDescriptor,
)
from dpost_v2.application.ingestion.stages.pipeline import PipelineTerminalOutcome
from dpost_v2.application.ingestion.stages.resolve import run_resolve_stage
from dpost_v2.application.ingestion.stages.route import run_route_stage
from dpost_v2.application.ingestion.stages.stabilize import run_stabilize_stage
from dpost_v2.application.ingestion.stages.transform import run_transform_stage
from dpost_v2.application.ingestion.state import IngestionState


class _Processor:
    def prepare(self, raw_input: dict[str, object]) -> dict[str, object]:
        return {**raw_input, "prepared": True}

    def can_process(self, candidate: dict[str, object]) -> bool:
        return bool(candidate.get("source_path"))

    def process(
        self,
        prepared_input: dict[str, object],
        _context: ProcessingContext,
    ) -> ProcessorResult:
        source_path = str(prepared_input["source_path"])
        extension = source_path.rsplit("/", maxsplit=1)[-1].rsplit(".", maxsplit=1)[0]
        return ProcessorResult(
            final_path=f"D:/normalized/{extension}.out",
            datatype="plug/output",
        )


class _RejectingProcessor(_Processor):
    def can_process(self, candidate: dict[str, object]) -> bool:
        return False


def _processing_context() -> ProcessingContext:
    runtime_context = RuntimeContext.from_settings(
        settings={
            "mode": "headless",
            "profile": "ci",
            "session_id": "session-stage",
            "event_id": "event-stage",
            "trace_id": "trace-stage",
        },
        dependency_ids={"clock": "clock-1", "ui": "ui-1", "sync": "sync-1"},
    )
    return ProcessingContext.for_candidate(
        runtime_context,
        {
            "source_path": "incoming/file.txt",
            "event_type": "created",
            "observed_at": datetime(2026, 3, 5),
        },
    )


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


def test_resolve_stage_rejects_empty_source_path() -> None:
    state = IngestionState(event={"event_kind": "created", "observed_at": 100.0})

    directive = run_resolve_stage(
        state,
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

    assert directive.kind == "terminal"
    assert directive.outcome is PipelineTerminalOutcome.REJECTED
    assert directive.state.diagnostics["resolve"]["reason_code"] == "invalid_candidate"


def test_resolve_stage_rejects_unsupported_event_kind() -> None:
    state = IngestionState(
        event={
            "path": "incoming/file.txt",
            "event_kind": "something_else",
            "observed_at": 100.0,
        }
    )

    directive = run_resolve_stage(
        state,
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

    assert directive.kind == "terminal"
    assert directive.outcome is PipelineTerminalOutcome.REJECTED
    assert directive.state.diagnostics["resolve"]["reason_code"] == "invalid_candidate"


def test_resolve_stage_allows_partial_event_with_default_observed_at() -> None:
    state = IngestionState(
        event={
            "path": "incoming/file.txt",
            "event_kind": "created",
        }
    )

    directive = run_resolve_stage(
        state,
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
    assert directive.state.candidate.observed_at == 0.0


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


def test_transform_stage_continues_to_route_with_validated_processor_result() -> None:
    candidate = Candidate.from_event(
        {"path": "incoming/file.txt", "event_kind": "created", "observed_at": 100.0},
        {"modified_at": 90.0},
    ).with_resolution("plug", "proc")
    state = IngestionState(
        event={},
        candidate=candidate,
        processor=_Processor(),
        processing_context=_processing_context(),
    )

    directive = run_transform_stage(state)

    assert directive.kind == "continue"
    assert directive.next_stage == "route"
    assert directive.state.processor_result is not None
    assert directive.state.processor_result.datatype == "plug/output"
    assert directive.state.prepared_input == {
        **candidate.to_payload(),
        "prepared": True,
    }


def test_transform_stage_defers_candidate_when_processor_is_not_ready() -> None:
    candidate = Candidate.from_event(
        {"path": "incoming/file.txt", "event_kind": "created", "observed_at": 100.0},
        {"modified_at": 90.0},
    ).with_resolution("plug", "proc")
    state = IngestionState(
        event={},
        candidate=candidate,
        processor=_RejectingProcessor(),
        processing_context=_processing_context(),
    )

    directive = run_transform_stage(state)

    assert directive.kind == "terminal"
    assert directive.outcome is PipelineTerminalOutcome.DEFERRED_STAGE
    assert directive.state.diagnostics["transform"]["reason_code"] == "deferred"


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
        filename_builder=lambda _state: "out.txt",
    )

    assert directive.kind == "terminal"
    assert directive.outcome is PipelineTerminalOutcome.REJECTED


def test_route_stage_continues_to_persist_when_target_is_valid() -> None:
    candidate = Candidate.from_event(
        {"path": "incoming/file.txt", "event_kind": "created", "observed_at": 100.0},
        {"modified_at": 90.0},
    ).with_resolution("plug", "proc")
    state = IngestionState(
        event={},
        candidate=candidate,
        processor_result=ProcessorResult(
            final_path="D:/normalized/file.out",
            datatype="plug/output",
        ),
    )

    directive = run_route_stage(
        state,
        allowed_roots=("C:/dest",),
        route_selector=lambda c: "C:/dest",
        filename_builder=lambda state: state.processor_result.final_path.rsplit(
            "/", maxsplit=1
        )[-1],
    )

    assert directive.kind == "continue"
    assert directive.next_stage == "persist"
    assert directive.state.candidate is not None
    assert directive.state.candidate.target_path == "C:/dest/file.out"
