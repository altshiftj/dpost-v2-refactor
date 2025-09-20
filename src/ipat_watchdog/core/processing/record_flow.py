"""Record interaction flows invoked by the processing pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from ipat_watchdog.core.interactions import (
    DialogPrompts,
    UserInteractionPort,
    WarningMessages,
)
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.processing.models import RouteContext, ProcessingResult, ProcessingStatus


def handle_unappendable_record(
    interactions: UserInteractionPort,
    rename_delegate: Callable[[str, str, str, str | None], ProcessingResult],
    context: RouteContext,
) -> ProcessingResult:
    """Display warning and redirect to rename flow when record cannot be appended."""
    candidate = context.candidate
    interactions.show_warning(
        WarningMessages.INVALID_RECORD,
        WarningMessages.INVALID_RECORD_DETAILS,
    )
    return rename_delegate(
        str(candidate.effective_path),
        context.sanitized_prefix,
        candidate.extension,
        contextual_reason=DialogPrompts.UNAPPENDABLE_RECORD_CONTEXT.format(
            record_id=context.sanitized_prefix
        ),
    )


def handle_append_to_synced_record(
    interactions: UserInteractionPort,
    add_item_delegate: Callable[[object, str, str, str, FileProcessorABS, bool], Optional[str]],
    rename_delegate: Callable[[str, str, str, str | None], ProcessingResult],
    context: RouteContext,
) -> ProcessingResult:
    """Prompt the user before appending to fully synced records."""
    candidate = context.candidate
    record = context.existing_record
    prefix = context.sanitized_prefix

    if interactions.prompt_append_record(prefix):
        final_path = add_item_delegate(
            record,
            str(candidate.effective_path),
            prefix,
            candidate.extension,
            candidate.processor,
            False,
        )
        return ProcessingResult(
            ProcessingStatus.PROCESSED,
            "Appended to synced record",
            None if final_path is None else Path(final_path),
        )

    return rename_delegate(
        str(candidate.effective_path),
        prefix,
        candidate.extension,
        contextual_reason=DialogPrompts.APPEND_RECORD_CANCEL_CONTEXT.format(record_id=prefix),
    )
