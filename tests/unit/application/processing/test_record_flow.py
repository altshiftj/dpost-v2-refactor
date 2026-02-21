"""Unit coverage for record-flow interaction redirection behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from dpost.application.interactions import DialogPrompts, WarningMessages
from dpost.application.processing.record_flow import handle_unappendable_record
from dpost.domain.processing.models import (
    ProcessingCandidate,
    ProcessingResult,
    ProcessingStatus,
    RouteContext,
    RoutingDecision,
)


@dataclass
class _InteractionSpy:
    """Capture warning calls emitted by record-flow handlers."""

    warnings: list[tuple[str, str]] = field(default_factory=list)

    def show_warning(self, title: str, message: str) -> None:
        """Record warning messages for assertion."""
        self.warnings.append((title, message))


def test_handle_unappendable_record_warns_and_redirects_to_rename_delegate() -> None:
    """Warn the user and route to rename flow with unappendable context message."""
    interactions = _InteractionSpy()
    candidate = ProcessingCandidate(
        original_path=Path("C:/records/sample.csv"),
        effective_path=Path("C:/records/sample.csv"),
        prefix="abc-ipat-sample",
        extension=".csv",
        processor=object(),
        device=object(),
    )
    context = RouteContext(
        candidate=candidate,
        sanitized_prefix="abc-ipat-sample",
        existing_record=None,
        decision=RoutingDecision.UNAPPENDABLE,
    )
    delegate_calls: list[tuple[str, str, str, str | None]] = []
    expected_result = ProcessingResult(
        status=ProcessingStatus.REJECTED,
        message="renamed",
    )

    def _rename_delegate(
        path: str,
        prefix: str,
        extension: str,
        contextual_reason: str | None,
    ) -> ProcessingResult:
        delegate_calls.append((path, prefix, extension, contextual_reason))
        return expected_result

    result = handle_unappendable_record(interactions, _rename_delegate, context)

    assert result is expected_result
    assert interactions.warnings == [
        (WarningMessages.INVALID_RECORD, WarningMessages.INVALID_RECORD_DETAILS)
    ]
    assert delegate_calls == [
        (
            str(candidate.effective_path),
            "abc-ipat-sample",
            ".csv",
            DialogPrompts.UNAPPENDABLE_RECORD_CONTEXT.format(
                record_id="abc-ipat-sample"
            ),
        )
    ]
