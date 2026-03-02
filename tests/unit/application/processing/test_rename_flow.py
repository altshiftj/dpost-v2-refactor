"""Unit coverage for interactive rename-flow loop and composition helpers."""

from __future__ import annotations

from dpost.application.ports import RenameDecision
from dpost.application.processing.rename_flow import RenameService


class _InteractionStub:
    """Interaction stub returning queued rename decisions."""

    def __init__(self, decisions: list[RenameDecision]) -> None:
        self._decisions = decisions
        self.prompts = []
        self.infos: list[tuple[str, str]] = []

    def request_rename(self, prompt):  # type: ignore[no-untyped-def]
        """Return next queued decision while recording prompt payload."""
        self.prompts.append(prompt)
        return self._decisions.pop(0)

    def show_info(self, title: str, message: str) -> None:
        """Record informational callback payloads for service assertions."""
        self.infos.append((title, message))


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
        lambda _attempted, **_kwargs: {
            "valid": False,
            "reasons": ["initial"],
            "highlight_spans": [],
        },
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
        lambda _values, **_kwargs: next(analyses),
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


def test_send_to_manual_bucket_forwards_explicit_rename_context(monkeypatch) -> None:
    """Manual bucket move should forward explicit rename context to storage helper."""
    interactions = _InteractionStub(decisions=[])
    service = RenameService(interactions)
    calls: dict[str, tuple[tuple[object, ...], dict[str, object]]] = {}

    monkeypatch.setattr(
        "dpost.application.processing.rename_flow.move_to_rename_folder",
        lambda *args, **kwargs: calls.__setitem__("move", (args, kwargs)),
    )

    service.send_to_manual_bucket(
        "C:/raw/file.txt",
        "prefix",
        ".txt",
        rename_dir="C:/rename",
        id_separator="__",
    )

    move_args, move_kwargs = calls["move"]
    assert move_args == ("C:/raw/file.txt", "prefix", ".txt")
    assert move_kwargs == {"base_dir": "C:/rename", "id_separator": "__"}
    assert interactions.infos


def test_obtain_valid_prefix_forwards_explicit_naming_context(monkeypatch) -> None:
    """Rename validation loop should forward explicit naming context to policy wrappers."""
    interactions = _InteractionStub(
        decisions=[
            RenameDecision(
                cancelled=False,
                values={"name": "mus", "institute": "ipat", "sample_ID": "sample"},
            )
        ]
    )
    service = RenameService(interactions)
    calls: dict[str, tuple[tuple[object, ...], dict[str, object]]] = {}

    monkeypatch.setattr(
        "dpost.application.processing.rename_flow.explain_filename_violation",
        lambda *args, **kwargs: calls.__setitem__("explain", (args, kwargs))
        or {"valid": False, "reasons": ["bad"], "highlight_spans": []},
    )
    monkeypatch.setattr(
        "dpost.application.processing.rename_flow.analyze_user_input",
        lambda *args, **kwargs: calls.__setitem__("analyze", (args, kwargs))
        or {"valid": True, "sanitized": "mus__ipat__sample", "reasons": []},
    )

    outcome = service.obtain_valid_prefix(
        "badprefix",
        filename_pattern=object(),  # type: ignore[arg-type]
        id_separator="__",
    )

    assert outcome.cancelled is False
    assert outcome.sanitized_prefix == "mus__ipat__sample"
    assert calls["explain"][1] == {
        "filename_pattern": calls["explain"][1]["filename_pattern"],
        "id_separator": "__",
    }
    assert calls["analyze"][1] == {
        "filename_pattern": calls["explain"][1]["filename_pattern"],
        "id_separator": "__",
    }


def test_obtain_valid_prefix_uses_explicit_separator_for_retry_attempt(monkeypatch) -> None:
    """Build retry attempted-prefix values using explicit naming separator context."""
    decisions = [
        RenameDecision(
            cancelled=False,
            values={"name": "u1", "institute": "ipat", "sample_ID": "bad!"},
        ),
        RenameDecision(
            cancelled=False,
            values={"name": "mus", "institute": "ipat", "sample_ID": "Sample_A"},
        ),
    ]
    interactions = _InteractionStub(decisions=decisions)
    service = RenameService(interactions)

    monkeypatch.setattr(
        "dpost.application.processing.rename_flow.explain_filename_violation",
        lambda _attempted, **_kwargs: {
            "valid": False,
            "reasons": ["initial"],
            "highlight_spans": [],
        },
    )
    analyses = iter(
        [
            {"valid": False, "sanitized": None, "reasons": ["bad"], "highlight_spans": []},
            {
                "valid": True,
                "sanitized": "mus__ipat__Sample_A",
                "reasons": [],
                "highlight_spans": [],
            },
        ]
    )
    monkeypatch.setattr(
        "dpost.application.processing.rename_flow.analyze_user_input",
        lambda _values, **_kwargs: next(analyses),
    )

    outcome = service.obtain_valid_prefix(
        current_prefix="invalid-prefix",
        id_separator="__",
    )

    assert outcome.cancelled is False
    assert outcome.sanitized_prefix == "mus__ipat__Sample_A"
    assert len(interactions.prompts) == 2
    assert interactions.prompts[1].attempted_prefix == "u1__ipat__bad!"
