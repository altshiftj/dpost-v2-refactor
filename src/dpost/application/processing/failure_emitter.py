"""Failure side-effect emission helpers for processing failures."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dpost.application.processing.failure_outcome_policy import ProcessingFailureOutcome


@dataclass(frozen=True)
class ProcessingFailureEmissionSink:
    """Injectable sink callables used to emit processing-failure side effects."""

    log_exception: Callable[[Path, Exception], None]
    move_to_exception: Callable[[str, str, str], None]
    register_rejection: Callable[[str, str], None]
    increment_failed_metric: Callable[[], None]


def emit_processing_failure_outcome(
    path: Path,
    exc: Exception,
    outcome: ProcessingFailureOutcome,
    sink: ProcessingFailureEmissionSink,
) -> None:
    """Emit all side effects for a classified processing failure outcome."""
    sink.log_exception(path, exc)

    for move_target in outcome.move_targets:
        sink.move_to_exception(
            move_target.path,
            move_target.prefix,
            move_target.extension,
        )

    sink.register_rejection(outcome.rejection_path, outcome.rejection_reason)
    sink.increment_failed_metric()
