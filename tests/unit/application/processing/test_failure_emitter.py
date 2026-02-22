"""Unit tests for processing failure side-effect emission helpers."""

from __future__ import annotations

from pathlib import Path

from dpost.application.processing.failure_emitter import (
    ProcessingFailureEmissionSink,
    emit_processing_failure_outcome,
)
from dpost.application.processing.failure_outcome_policy import (
    FailureMoveTarget,
    ProcessingFailureOutcome,
)


def test_emit_processing_failure_outcome_emits_all_sinks_in_order() -> None:
    """Emit log, moves, rejection, and metric increment from a failure outcome."""
    calls: list[tuple[str, object]] = []
    sink = ProcessingFailureEmissionSink(
        log_exception=lambda path, exc: calls.append(("log", (path, str(exc)))),
        move_to_exception=lambda path, prefix, extension: calls.append(
            ("move", (path, prefix, extension))
        ),
        register_rejection=lambda path, reason: calls.append(
            ("reject", (path, reason))
        ),
        increment_failed_metric=lambda: calls.append(("metric", None)),
    )
    outcome = ProcessingFailureOutcome(
        move_targets=(
            FailureMoveTarget("C:/watch/a.txt", "a", ".txt"),
            FailureMoveTarget("C:/watch/a.__staged__.txt", "a", ".txt"),
        ),
        rejection_path="C:/watch/a.txt",
        rejection_reason="boom",
    )

    emit_processing_failure_outcome(
        Path("C:/watch/a.txt"),
        RuntimeError("boom"),
        outcome,
        sink,
    )

    assert calls == [
        ("log", (Path("C:/watch/a.txt"), "boom")),
        ("move", ("C:/watch/a.txt", "a", ".txt")),
        ("move", ("C:/watch/a.__staged__.txt", "a", ".txt")),
        ("reject", ("C:/watch/a.txt", "boom")),
        ("metric", None),
    ]
