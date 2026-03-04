"""Unit tests for V2 domain processing outcome models."""

from __future__ import annotations

import pytest

from dpost_v2.domain.processing.models import (
    ProcessingOutcome,
    ProcessingOutcomeConsistencyError,
    ProcessingOutcomeMetadataError,
    ProcessingReason,
    ProcessingReasonNamespaceError,
    ProcessingStatus,
    ProcessingStatusError,
    failed_outcome,
    outcome_from_classification,
    outcome_from_dict,
    retry_outcome,
    success_outcome,
)


def test_success_outcome_factory_builds_valid_outcome() -> None:
    """Construct a valid success outcome with deterministic fields."""
    outcome = success_outcome(candidate_id="cand-1", reason_code="stored")

    assert outcome.status is ProcessingStatus.SUCCESS
    assert outcome.reason.namespace == "success"
    assert outcome.reason.code == "stored"
    assert outcome.retry_delay_seconds is None
    assert outcome.retry_attempt is None


def test_retry_outcome_factory_requires_retry_metadata() -> None:
    """Retry outcomes must include delay and attempt metadata."""
    with pytest.raises(ProcessingOutcomeMetadataError):
        ProcessingOutcome(
            candidate_id="cand-1",
            status=ProcessingStatus.RETRY,
            reason=ProcessingReason(namespace="retry", code="stabilizing"),
            retry_delay_seconds=None,
            retry_attempt=1,
        )


def test_non_retry_outcome_rejects_retry_metadata() -> None:
    """Non-retry outcomes should not include retry-specific fields."""
    with pytest.raises(ProcessingOutcomeMetadataError):
        ProcessingOutcome(
            candidate_id="cand-2",
            status=ProcessingStatus.SUCCESS,
            reason=ProcessingReason(namespace="success", code="stored"),
            retry_delay_seconds=5.0,
            retry_attempt=1,
        )


def test_success_outcome_rejects_failure_reason_namespace() -> None:
    """Reject invalid status/reason namespace combinations."""
    with pytest.raises(ProcessingOutcomeConsistencyError):
        ProcessingOutcome(
            candidate_id="cand-3",
            status=ProcessingStatus.SUCCESS,
            reason=ProcessingReason(namespace="failure", code="disk_full"),
        )


def test_reason_rejects_unknown_namespace() -> None:
    """Reject unknown reason namespaces with typed error."""
    with pytest.raises(ProcessingReasonNamespaceError):
        ProcessingReason(namespace="not_a_namespace", code="x")


def test_processing_outcome_serialization_round_trip() -> None:
    """Outcome serialization/deserialization should be stable and deterministic."""
    original = retry_outcome(
        candidate_id="cand-4",
        reason_code="backoff",
        retry_delay_seconds=2.5,
        retry_attempt=3,
        metadata={"profile": "prod"},
    )

    as_dict = original.to_dict()
    restored = outcome_from_dict(as_dict)

    assert restored == original


def test_outcome_from_classification_rejects_unknown_status() -> None:
    """Reject policy status tokens outside enum values."""
    with pytest.raises(ProcessingStatusError):
        outcome_from_classification(
            candidate_id="cand-5",
            status_token="maybe",
            reason_token="success.stored",
        )


def test_failed_outcome_factory_sets_failure_namespace() -> None:
    """Failure constructor should emit failed status with failure namespace."""
    outcome = failed_outcome(
        candidate_id="cand-6",
        reason_code="io_error",
        metadata={"device_family": "rheometer"},
    )

    assert outcome.status is ProcessingStatus.FAILED
    assert outcome.reason.namespace == "failure"
