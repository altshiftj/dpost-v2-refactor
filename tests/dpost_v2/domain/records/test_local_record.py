"""Unit tests for V2 domain local-record entity invariants."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from dpost_v2.domain.records.local_record import (
    LocalRecordIdentityError,
    LocalRecordTimestampError,
    LocalRecordTransitionError,
    RecordProcessingStatus,
    SyncStatus,
    apply_processing_result,
    create_record,
    differs_by_revision,
    mark_synced,
    mark_unsynced,
    same_identity,
)


def _ts(hour: int) -> datetime:
    return datetime(2026, 3, 4, hour, 0, 0, tzinfo=timezone.utc)


def test_create_record_rejects_missing_identity_fields() -> None:
    """Record creation requires non-empty identity attributes."""
    with pytest.raises(LocalRecordIdentityError):
        create_record(
            record_id="",
            source_identity="src-1",
            canonical_name="rhe-sample-1",
            created_at=_ts(10),
        )


def test_record_identity_fields_remain_stable_across_mutations() -> None:
    """Identity fields must not change after legal record mutations."""
    record = create_record(
        record_id="rec-1",
        source_identity="src-1",
        canonical_name="rhe-sample-1",
        created_at=_ts(10),
    )

    synced = mark_synced(record, updated_at=_ts(11))

    assert synced.record_id == "rec-1"
    assert synced.source_identity == "src-1"
    assert synced.canonical_name == "rhe-sample-1"


def test_revision_is_monotonic_for_accepted_mutations() -> None:
    """Each accepted mutation should increment revision deterministically."""
    record = create_record(
        record_id="rec-2",
        source_identity="src-2",
        canonical_name="rhe-sample-2",
        created_at=_ts(10),
    )
    synced = mark_synced(record, updated_at=_ts(11))
    processed = apply_processing_result(
        synced,
        processing_status=RecordProcessingStatus.PROCESSED,
        updated_at=_ts(12),
    )

    assert record.revision == 0
    assert synced.revision == 1
    assert processed.revision == 2


def test_sync_state_transitions_allow_synced_to_unsynced() -> None:
    """Allow legal sync graph transitions via explicit mutation helpers."""
    record = create_record(
        record_id="rec-3",
        source_identity="src-3",
        canonical_name="rhe-sample-3",
        created_at=_ts(10),
    )

    synced = mark_synced(record, updated_at=_ts(11))
    unsynced = mark_unsynced(synced, updated_at=_ts(12))

    assert synced.sync_status is SyncStatus.SYNCED
    assert unsynced.sync_status is SyncStatus.UNSYNCED


def test_sync_state_transitions_reject_illegal_unsynced_to_unsynced() -> None:
    """Reject illegal sync transition attempts."""
    record = create_record(
        record_id="rec-4",
        source_identity="src-4",
        canonical_name="rhe-sample-4",
        created_at=_ts(10),
    )
    with pytest.raises(LocalRecordTransitionError):
        mark_unsynced(record, updated_at=_ts(11))


def test_record_mutations_reject_timestamp_regression() -> None:
    """Reject mutation timestamps older than current record timestamp."""
    record = create_record(
        record_id="rec-5",
        source_identity="src-5",
        canonical_name="rhe-sample-5",
        created_at=_ts(10),
    )
    synced = mark_synced(record, updated_at=_ts(11))
    with pytest.raises(LocalRecordTimestampError):
        apply_processing_result(
            synced,
            processing_status=RecordProcessingStatus.PROCESSED,
            updated_at=_ts(10),
        )


def test_record_comparison_helpers_distinguish_identity_vs_revision() -> None:
    """Expose helper semantics for identity equality and revision differences."""
    record = create_record(
        record_id="rec-6",
        source_identity="src-6",
        canonical_name="rhe-sample-6",
        created_at=_ts(10),
    )
    synced = mark_synced(record, updated_at=_ts(11))

    assert same_identity(record, synced) is True
    assert differs_by_revision(record, synced) is True
