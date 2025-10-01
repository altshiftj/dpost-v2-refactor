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
from ipat_watchdog.core.records.local_record import LocalRecord


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


# NOTE: The append-to-synced prompt flow has been removed for the
# 'it just works' mode. Appending to an already-synced record now proceeds
# automatically via the ACCEPT path with no user interaction.
