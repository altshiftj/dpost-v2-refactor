"""Unit coverage for interactive rename-flow loop and composition helpers."""

from __future__ import annotations

from dpost.application.ports import RenameDecision
from dpost.application.processing.rename_flow import RenameService


class _InteractionStub:
    """Interaction stub returning queued rename decisions."""

    def __init__(self, decisions: list[RenameDecision]) -> None:
        self._decisions = decisions
        self.prompts = []

    def request_rename(self, prompt):  # type: ignore[no-untyped-def]
        """Return next queued decision while recording prompt payload."""
        self.prompts.append(prompt)
        return self._decisions.pop(0)

    def show_info(self, _title: str, _message: str) -> None:
        """No-op informational callback for service compatibility."""


def test_obtain_valid_prefix_retries_until_analysis_is_valid(monkeypatch) -> None:
    """Loop through rename prompts until analysis validates and returns sanitized prefix."""
    decisions = [
        RenameDecision(
            cancelled=False,
            values={"name": "u1", "institute": "ipat", "sample_ID": "bad!"},
        ),
        RenameDecision(
            cancelled=False,
            values={"name": "mus", "institute": "ipat", "sample_ID": "Sample A"},
        ),
    ]
    interactions = _InteractionStub(decisions=decisions)
    service = RenameService(interactions)

    monkeypatch.setattr(
        "dpost.application.processing.rename_flow.explain_filename_violation",
        lambda _attempted: {"valid": False, "reasons": ["initial"], "highlight_spans": []},
    )
    analyses = iter(
        [
            {"valid": False, "sanitized": None, "reasons": ["bad"], "highlight_spans": []},
            {
                "valid": True,
                "sanitized": "mus-ipat-Sample_A",
                "reasons": [],
                "highlight_spans": [],
            },
        ]
    )
    monkeypatch.setattr(
        "dpost.application.processing.rename_flow.analyze_user_input",
        lambda _values: next(analyses),
    )

    outcome = service.obtain_valid_prefix(
        current_prefix="invalid-prefix",
        contextual_reason="record exists",
    )

    assert outcome.cancelled is False
    assert outcome.sanitized_prefix == "mus-ipat-Sample_A"
    assert len(interactions.prompts) == 2
    assert interactions.prompts[0].attempted_prefix == "invalid-prefix"
    assert interactions.prompts[0].contextual_reason == "record exists"
    assert interactions.prompts[1].attempted_prefix == "u1-ipat-bad!"
    assert interactions.prompts[1].contextual_reason is None


def test_compose_attempted_prefix_joins_expected_fields() -> None:
    """Join rename user/institute/sample values into attempted prefix."""
    attempted = RenameService._compose_attempted_prefix(  # noqa: SLF001
        {"name": "mus", "institute": "ipat", "sample_ID": "Sample_A"}
    )
    assert attempted == "mus-ipat-Sample_A"
