from __future__ import annotations

from typing import Mapping

from dpost_v2.application.contracts.plugin_contracts import validate_processor_result
from dpost_v2.application.ingestion.stages.pipeline import (
    PipelineTerminalOutcome,
    StageDirective,
)
from dpost_v2.application.ingestion.state import IngestionState


def run_transform_stage(state: IngestionState) -> StageDirective[IngestionState]:
    """Execute processor prepare/can_process/process and store validated output."""
    candidate = state.candidate
    processor = state.processor
    processing_context = state.processing_context
    if candidate is None or processor is None or processing_context is None:
        failed = state.with_updates(
            diagnostics={"transform": {"reason_code": "missing_processing_context"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)

    raw_input = candidate.to_payload()
    prepare = getattr(processor, "prepare", None)
    try:
        prepared_input = prepare(raw_input) if callable(prepare) else raw_input
    except Exception:  # noqa: BLE001
        failed = state.with_updates(
            diagnostics={"transform": {"reason_code": "prepare_failed"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)

    if not isinstance(prepared_input, Mapping):
        failed = state.with_updates(
            diagnostics={"transform": {"reason_code": "invalid_prepared_input"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)

    can_process = getattr(processor, "can_process", None)
    if callable(can_process):
        try:
            supported = bool(can_process(prepared_input))
        except Exception:  # noqa: BLE001
            supported = False
        if not supported:
            deferred = state.with_updates(
                diagnostics={
                    "transform": {
                        "reason_code": "deferred",
                        "prepared_kind": str(
                            prepared_input.get("prepared_kind", "")
                        ).strip(),
                    }
                }
            )
            return StageDirective.terminal(
                PipelineTerminalOutcome.DEFERRED_STAGE,
                deferred,
            )

    process = getattr(processor, "process", None)
    if not callable(process):
        failed = state.with_updates(
            diagnostics={"transform": {"reason_code": "missing_process"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)

    try:
        processor_result = validate_processor_result(
            process(dict(prepared_input), processing_context)
        )
    except Exception:  # noqa: BLE001
        failed = state.with_updates(
            diagnostics={"transform": {"reason_code": "process_failed"}}
        )
        return StageDirective.terminal(PipelineTerminalOutcome.FAILED, failed)

    next_state = state.with_updates(
        prepared_input=dict(prepared_input),
        processor_result=processor_result,
        diagnostics={
            "transform": {
                "reason_code": "processed",
                "datatype": processor_result.datatype,
            }
        },
    )
    return StageDirective.continue_to("route", next_state)
