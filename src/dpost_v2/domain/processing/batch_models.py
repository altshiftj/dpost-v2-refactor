"""Batch outcome aggregation models for V2 processing domain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Mapping, Sequence

from dpost_v2.domain.processing.models import ProcessingOutcome


class BatchModelError(ValueError):
    """Base class for batch-model domain errors."""


class BatchMemberDuplicateError(BatchModelError):
    """Raised when a batch contains duplicate member identity keys."""


class BatchCountConsistencyError(BatchModelError):
    """Raised when aggregate counts mismatch expected/member totals."""


class BatchMetadataError(BatchModelError):
    """Raised when required batch identity metadata is missing/invalid."""


class BatchStatus(str, Enum):
    """Batch-level terminal status derived from member outcomes."""

    COMPLETED = "completed"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


@dataclass(frozen=True)
class BatchOutcome:
    """Immutable aggregate view of grouped processing outcomes."""

    batch_id: str
    started_at: datetime
    completed_at: datetime
    members: tuple[ProcessingOutcome, ...]
    counts: Mapping[str, int]
    grouped_counts: Mapping[tuple[str, ...], Mapping[str, int]]
    status: BatchStatus


def _empty_counts() -> dict[str, int]:
    return {
        "total": 0,
        "success": 0,
        "rejected": 0,
        "failed": 0,
        "retry": 0,
    }


def _derive_status(counts: Mapping[str, int]) -> BatchStatus:
    total = counts["total"]
    failures = counts["failed"] + counts["rejected"]
    retries = counts["retry"]
    if total == 0:
        return BatchStatus.FAILED
    if failures == 0 and retries == 0:
        return BatchStatus.COMPLETED
    if failures == total:
        return BatchStatus.FAILED
    return BatchStatus.PARTIAL_FAILURE


def _validate_metadata(
    *,
    batch_id: str,
    started_at: datetime,
    completed_at: datetime,
) -> None:
    if not batch_id:
        raise BatchMetadataError("batch_id must be non-empty.")
    if started_at is None or completed_at is None:
        raise BatchMetadataError("started_at and completed_at are required.")
    if completed_at < started_at:
        raise BatchMetadataError("completed_at must be >= started_at.")


def _accumulate_group_counts(
    members: Sequence[ProcessingOutcome],
    grouping_keys: Sequence[str],
) -> dict[tuple[str, ...], dict[str, int]]:
    grouped: dict[tuple[str, ...], dict[str, int]] = {}
    for outcome in members:
        group_key = tuple(outcome.metadata.get(key, "") for key in grouping_keys)
        counts = grouped.setdefault(group_key, _empty_counts())
        counts["total"] += 1
        counts[outcome.status.value] += 1
    return grouped


def build_batch_outcome(
    *,
    batch_id: str,
    started_at: datetime,
    completed_at: datetime,
    members: Sequence[ProcessingOutcome],
    grouping_keys: Sequence[str] = (),
    expected_count: int | None = None,
) -> BatchOutcome:
    """Build immutable batch outcome with validated aggregate consistency."""
    _validate_metadata(
        batch_id=batch_id, started_at=started_at, completed_at=completed_at
    )

    seen_ids: set[str] = set()
    counts = _empty_counts()
    frozen_members: list[ProcessingOutcome] = []
    for outcome in members:
        if outcome.candidate_id in seen_ids:
            raise BatchMemberDuplicateError(
                f"Duplicate batch member identity '{outcome.candidate_id}'.",
            )
        seen_ids.add(outcome.candidate_id)
        frozen_members.append(outcome)
        counts["total"] += 1
        counts[outcome.status.value] += 1

    if expected_count is not None and expected_count != counts["total"]:
        raise BatchCountConsistencyError(
            "Expected batch count does not match unique member total.",
        )

    grouped_counts = _accumulate_group_counts(frozen_members, grouping_keys)
    status = _derive_status(counts)
    return BatchOutcome(
        batch_id=batch_id,
        started_at=started_at,
        completed_at=completed_at,
        members=tuple(frozen_members),
        counts=counts,
        grouped_counts=grouped_counts,
        status=status,
    )
