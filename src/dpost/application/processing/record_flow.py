"""Record interaction flows invoked by the processing pipeline."""

from __future__ import annotations

from typing import Callable

from dpost.application.interactions import DialogPrompts, WarningMessages
from dpost.application.ports import UserInteractionPort
from dpost.application.processing.models import ProcessingResult, RouteContext


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
        DialogPrompts.UNAPPENDABLE_RECORD_CONTEXT.format(
            record_id=context.sanitized_prefix
        ),
    )
