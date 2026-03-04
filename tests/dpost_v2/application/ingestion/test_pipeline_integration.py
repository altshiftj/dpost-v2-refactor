from __future__ import annotations

from dpost_v2.application.ingestion.engine import IngestionEngine, IngestionOutcomeKind
from dpost_v2.application.ingestion.processor_factory import (
    ProcessorSelection,
    SelectionDescriptor,
)
from dpost_v2.application.ingestion.stages.persist import run_persist_stage
from dpost_v2.application.ingestion.stages.pipeline import (
    DEFAULT_INGESTION_TRANSITION_TABLE,
    PipelineRunner,
)
from dpost_v2.application.ingestion.stages.post_persist import run_post_persist_stage
from dpost_v2.application.ingestion.stages.resolve import run_resolve_stage
from dpost_v2.application.ingestion.stages.route import run_route_stage
from dpost_v2.application.ingestion.stages.stabilize import run_stabilize_stage
from dpost_v2.application.ingestion.state import IngestionState


class _Processor:
    def process(self) -> None:
        return None


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
        "route": lambda state: run_route_stage(
            state,
            allowed_roots=("C:/dest",),
            route_selector=lambda c: "C:/dest",
            filename_builder=lambda c: "file.txt",
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
        initial_state_factory=IngestionState.from_event,
    )

    assert outcome.kind is IngestionOutcomeKind.SUCCEEDED
    assert outcome.final_stage_id == "post_persist"
