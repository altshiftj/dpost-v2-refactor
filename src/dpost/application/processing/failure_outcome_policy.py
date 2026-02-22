"""Pure policy helpers for classifying processing-failure artefact moves."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dpost.domain.processing.models import ProcessingCandidate


@dataclass(frozen=True)
class FailureMoveTarget:
    """A file-system target to move as part of processing failure cleanup."""

    path: str
    prefix: str
    extension: str


@dataclass(frozen=True)
class ProcessingFailureOutcome:
    """Pure failure-classification output consumed by side-effect handlers."""

    move_targets: tuple[FailureMoveTarget, ...]
    rejection_path: str
    rejection_reason: str


def build_failure_move_targets(
    path: Path,
    candidate: ProcessingCandidate | None,
) -> tuple[FailureMoveTarget, ...]:
    """Return the artefact move targets required for a processing failure."""
    if candidate is None:
        return (
            FailureMoveTarget(
                path=str(path),
                prefix=path.stem,
                extension=path.suffix,
            ),
        )

    targets: list[FailureMoveTarget] = [
        FailureMoveTarget(
            path=str(candidate.effective_path),
            prefix=candidate.prefix,
            extension=candidate.extension,
        )
    ]

    if (
        candidate.preprocessed_path
        and candidate.preprocessed_path != candidate.effective_path
    ):
        targets.append(
            FailureMoveTarget(
                path=str(candidate.preprocessed_path),
                prefix=candidate.prefix,
                extension=candidate.extension,
            )
        )

    return tuple(targets)


def build_processing_failure_outcome(
    path: Path,
    candidate: ProcessingCandidate | None,
    exc: Exception,
) -> ProcessingFailureOutcome:
    """Build move targets and rejection payload for a processing failure."""
    return ProcessingFailureOutcome(
        move_targets=build_failure_move_targets(path, candidate),
        rejection_path=str(path),
        rejection_reason=str(exc),
    )
