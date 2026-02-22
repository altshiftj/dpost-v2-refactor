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
