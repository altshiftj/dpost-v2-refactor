"""Record domain entities for V2."""

from dpost_v2.domain.records.local_record import (
    LocalRecord,
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

__all__ = [
    "LocalRecord",
    "LocalRecordIdentityError",
    "LocalRecordTimestampError",
    "LocalRecordTransitionError",
    "RecordProcessingStatus",
    "SyncStatus",
    "apply_processing_result",
    "create_record",
    "differs_by_revision",
    "mark_synced",
    "mark_unsynced",
    "same_identity",
]

