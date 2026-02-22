"""Pure policy helpers for rename-loop retry prompts and warnings."""

from __future__ import annotations

from dataclasses import dataclass

from dpost.application.interactions import DialogPrompts, WarningMessages
from dpost.domain.processing.models import RouteContext, RoutingDecision


@dataclass(frozen=True)
class RenameRetryPromptPolicy:
    """Policy output for the next rename prompt iteration."""

    next_prefix: str
    contextual_reason: str | None
    warning_title: str | None = None
    warning_message: str | None = None


def build_rename_retry_prompt(context: RouteContext) -> RenameRetryPromptPolicy:
    """Return prompt/warning policy for the next rename retry iteration."""
    if context.decision is RoutingDecision.UNAPPENDABLE:
        return RenameRetryPromptPolicy(
            next_prefix=context.sanitized_prefix,
            contextual_reason=DialogPrompts.UNAPPENDABLE_RECORD_CONTEXT.format(
                record_id=context.sanitized_prefix
            ),
            warning_title=WarningMessages.INVALID_RECORD,
            warning_message=WarningMessages.INVALID_RECORD_DETAILS,
        )

    return RenameRetryPromptPolicy(
        next_prefix=context.candidate.prefix,
        contextual_reason=None,
    )
