"""Unit tests for V2 domain batch processing models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from dpost_v2.domain.processing.batch_models import (
    BatchCountConsistencyError,
    BatchMemberDuplicateError,
    BatchMetadataError,
    BatchStatus,
    build_batch_outcome,
)
from dpost_v2.domain.processing.models import (
    failed_outcome,
    rejected_outcome,
    retry_outcome,
    success_outcome,
)


def _ts(hour: int) -> datetime:
    return datetime(2026, 3, 4, hour, 0, 0, tzinfo=timezone.utc)


def test_build_batch_outcome_rejects_duplicate_member_identity() -> None:
    """Reject duplicate candidate identities inside a single batch."""
    members = (
        success_outcome(candidate_id="cand-1", reason_code="stored"),
        retry_outcome(
            candidate_id="cand-1",
            reason_code="waiting",
            retry_delay_seconds=2.0,
            retry_attempt=1,
        ),
    )

    with pytest.raises(BatchMemberDuplicateError):
        build_batch_outcome(
            batch_id="batch-1",
            started_at=_ts(10),
            completed_at=_ts(11),
            members=members,
        )


def test_build_batch_outcome_aggregates_counts_consistently() -> None:
    """Aggregate status counts must match unique member total."""
    members = (
        success_outcome(candidate_id="cand-1", reason_code="stored"),
        retry_outcome(
            candidate_id="cand-2",
            reason_code="waiting",
            retry_delay_seconds=1.0,
            retry_attempt=1,
            metadata={"profile": "prod"},
        ),
        rejected_outcome(candidate_id="cand-3", reason_code="invalid_name"),
    )

    result = build_batch_outcome(
        batch_id="batch-2",
        started_at=_ts(10),
        completed_at=_ts(11),
        members=members,
        grouping_keys=("profile",),
    )

    assert result.counts["total"] == 3
    assert result.counts["success"] == 1
    assert result.counts["retry"] == 1
    assert result.counts["rejected"] == 1
    assert result.status is BatchStatus.PARTIAL_FAILURE


def test_build_batch_outcome_derives_completed_for_all_success() -> None:
    """All-success member outcomes should derive completed batch status."""
    members = (
        success_outcome(candidate_id="cand-1", reason_code="stored"),
        success_outcome(candidate_id="cand-2", reason_code="stored"),
    )

    result = build_batch_outcome(
        batch_id="batch-3",
        started_at=_ts(10),
        completed_at=_ts(11),
        members=members,
    )

    assert result.status is BatchStatus.COMPLETED


def test_build_batch_outcome_derives_failed_for_all_failed_like_members() -> None:
    """All rejected/failed members should derive failed batch status."""
    members = (
        failed_outcome(candidate_id="cand-1", reason_code="io_error"),
        rejected_outcome(candidate_id="cand-2", reason_code="invalid_name"),
    )

    result = build_batch_outcome(
        batch_id="batch-4",
        started_at=_ts(10),
        completed_at=_ts(11),
        members=members,
    )

    assert result.status is BatchStatus.FAILED


def test_build_batch_outcome_rejects_declared_count_mismatch() -> None:
    """Reject batch payloads whose expected count mismatches unique members."""
    members = (success_outcome(candidate_id="cand-1", reason_code="stored"),)

    with pytest.raises(BatchCountConsistencyError):
        build_batch_outcome(
            batch_id="batch-5",
            started_at=_ts(10),
            completed_at=_ts(11),
            members=members,
            expected_count=2,
        )


def test_build_batch_outcome_rejects_missing_batch_metadata() -> None:
    """Reject missing identity/timestamp metadata required for batch outcomes."""
    with pytest.raises(BatchMetadataError):
        build_batch_outcome(
            batch_id="",
            started_at=_ts(10),
            completed_at=_ts(11),
            members=(),
        )


def test_build_batch_outcome_exposes_grouped_summary_counts() -> None:
    """Grouped summaries should preserve deterministic aggregate counts per key."""
    members = (
        success_outcome(
            candidate_id="cand-1",
            reason_code="stored",
            metadata={"profile": "prod", "device_family": "rheometer"},
        ),
        failed_outcome(
            candidate_id="cand-2",
            reason_code="io_error",
            metadata={"profile": "prod", "device_family": "rheometer"},
        ),
        success_outcome(
            candidate_id="cand-3",
            reason_code="stored",
            metadata={"profile": "qa", "device_family": "rheometer"},
        ),
    )

    result = build_batch_outcome(
        batch_id="batch-6",
        started_at=_ts(10),
        completed_at=_ts(11),
        members=members,
        grouping_keys=("profile", "device_family"),
    )

    assert result.grouped_counts[("prod", "rheometer")]["total"] == 2
    assert result.grouped_counts[("prod", "rheometer")]["failed"] == 1
    assert result.grouped_counts[("qa", "rheometer")]["success"] == 1
