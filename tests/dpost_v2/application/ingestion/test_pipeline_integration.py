from __future__ import annotations

from datetime import datetime

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext
from dpost_v2.application.contracts.plugin_contracts import ProcessorResult
from dpost_v2.application.ingestion.engine import IngestionEngine, IngestionOutcomeKind
from dpost_v2.application.ingestion.processor_factory import (
    ProcessorSelection,
    SelectionDescriptor,
)
from dpost_v2.application.ingestion.stages.persist import run_persist_stage
from dpost_v2.application.ingestion.stages.pipeline import (
    DEFAULT_INGESTION_TRANSITION_TABLE,
    PipelineRunner,
    PipelineTerminalOutcome,
    StageDirective,
)
from dpost_v2.application.ingestion.stages.post_persist import run_post_persist_stage
from dpost_v2.application.ingestion.stages.resolve import run_resolve_stage
from dpost_v2.application.ingestion.stages.route import run_route_stage
from dpost_v2.application.ingestion.stages.stabilize import run_stabilize_stage
from dpost_v2.application.ingestion.stages.transform import run_transform_stage
from dpost_v2.application.ingestion.state import IngestionState


class _Processor:
    def prepare(self, raw_input: dict[str, object]) -> dict[str, object]:
        return dict(raw_input)

    def can_process(self, candidate: dict[str, object]) -> bool:
        return bool(candidate.get("source_path"))

    def process(
        self,
        prepared_input: dict[str, object],
        _context: ProcessingContext,
    ) -> ProcessorResult:
        return ProcessorResult(
            final_path=str(prepared_input["source_path"]),
            datatype="plug/output",
        )


def _processing_context() -> ProcessingContext:
    runtime_context = RuntimeContext.from_settings(
        settings={
            "mode": "headless",
            "profile": "ci",
            "session_id": "session-pipeline",
            "event_id": "event-pipeline",
            "trace_id": "trace-pipeline",
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


def test_full_ingestion_pipeline_happy_path() -> None:
    handlers = {
        "resolve": lambda state: run_resolve_stage(
            state,
            fs_facts_provider=lambda path: {"modified_at": 90.0},
            processor_selector=lambda candidate: ProcessorSelection(
                processor=_Processor(),
                descriptor=SelectionDescriptor(
                    plugin_id="plug",
                    processor_key="proc",
                    capability_reason="ok",
                    cache_hit=False,
                ),
            ),
        ),
        "stabilize": lambda state: run_stabilize_stage(
            state,
            modified_event_gate=lambda key, ts: type(
                "GateResult", (), {"decision": "allow", "reason_code": "ok"}
            )(),
            now_provider=lambda: 100.0,
            settle_delay_seconds=5.0,
        ),
        "transform": lambda state: run_transform_stage(state),
        "route": lambda state: run_route_stage(
            state,
            allowed_roots=("C:/dest",),
            route_selector=lambda c: "C:/dest",
            filename_builder=lambda _state: "file.txt",
        ),
        "persist": lambda state: run_persist_stage(
            state,
            move_file=lambda source, target: type(
                "Call", (), {"status": "success", "value": target, "diagnostics": {}}
            )(),
            save_record=lambda payload: type(
                "Call",
                (),
                {"status": "success", "value": {"record_id": "r1"}, "diagnostics": {}},
            )(),
            retry_planner=lambda reason, attempt: {"terminal_type": "stop_retrying"},
        ),
        "post_persist": lambda state: run_post_persist_stage(
            state,
            update_bookkeeping=lambda record_id, candidate: type(
                "Call", (), {"status": "success", "value": True, "diagnostics": {}}
            )(),
            trigger_sync=lambda record_id: type(
                "Call", (), {"status": "success", "value": True, "diagnostics": {}}
            )(),
            emit_sync_error=lambda event_id, record_id, reason: None,
            immediate_sync_enabled=True,
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
        event={
            "path": "incoming/file.txt",
            "event_kind": "created",
            "observed_at": 100.0,
        },
        initial_state_factory=lambda event: IngestionState.from_event(
            event,
            processing_context=_processing_context(),
        ),
    )

    assert outcome.kind is IngestionOutcomeKind.SUCCEEDED
    assert outcome.final_stage_id == "post_persist"


def test_full_ingestion_pipeline_maps_transform_retry_to_deferred_retry() -> None:
    handlers = {
        "resolve": lambda state: run_resolve_stage(
            state,
            fs_facts_provider=lambda path: {"modified_at": 90.0},
            processor_selector=lambda candidate: ProcessorSelection(
                processor=_Processor(),
                descriptor=SelectionDescriptor(
                    plugin_id="plug",
                    processor_key="proc",
                    capability_reason="ok",
                    cache_hit=False,
                ),
            ),
        ),
        "stabilize": lambda state: run_stabilize_stage(
            state,
            modified_event_gate=lambda key, ts: type(
                "GateResult", (), {"decision": "allow", "reason_code": "ok"}
            )(),
            now_provider=lambda: 100.0,
            settle_delay_seconds=5.0,
        ),
        "transform": lambda state: StageDirective.terminal(
            PipelineTerminalOutcome.RETRY,
            state,
        ),
        "route": lambda state: run_route_stage(
            state,
            allowed_roots=("C:/dest",),
            route_selector=lambda c: "C:/dest",
            filename_builder=lambda _state: "file.txt",
        ),
        "persist": lambda state: run_persist_stage(
            state,
            move_file=lambda source, target: type(
                "Call", (), {"status": "success", "value": target, "diagnostics": {}}
            )(),
            save_record=lambda payload: type(
                "Call",
                (),
                {"status": "success", "value": {"record_id": "r1"}, "diagnostics": {}},
            )(),
            retry_planner=lambda reason, attempt: {"terminal_type": "stop_retrying"},
        ),
        "post_persist": lambda state: run_post_persist_stage(
            state,
            update_bookkeeping=lambda record_id, candidate: type(
                "Call", (), {"status": "success", "value": True, "diagnostics": {}}
            )(),
            trigger_sync=lambda record_id: type(
                "Call", (), {"status": "success", "value": True, "diagnostics": {}}
            )(),
            emit_sync_error=lambda event_id, record_id, reason: None,
            immediate_sync_enabled=True,
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
        event={
            "path": "incoming/file.txt",
            "event_kind": "created",
            "observed_at": 100.0,
        },
        initial_state_factory=lambda event: IngestionState.from_event(
            event,
            processing_context=_processing_context(),
        ),
    )

    assert outcome.kind is IngestionOutcomeKind.DEFERRED_RETRY
    assert outcome.final_stage_id == "transform"
