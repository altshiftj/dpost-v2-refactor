"""Local record entity and mutation invariants for V2 domain."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Mapping


class LocalRecordError(ValueError):
    """Base class for local record domain errors."""


class LocalRecordIdentityError(LocalRecordError):
    """Raised when record identity fields are missing/invalid."""


class LocalRecordTransitionError(LocalRecordError):
    """Raised when requested status transition is illegal."""


class LocalRecordTimestampError(LocalRecordError):
    """Raised when timestamp ordering invariants are violated."""


class SyncStatus(str, Enum):
    """Sync state graph for local records."""

    UNSYNCED = "unsynced"
    SYNCED = "synced"


class RecordProcessingStatus(str, Enum):
    """Processing status tracked on local record entity."""

    PENDING = "pending"
    PROCESSED = "processed"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True)
class LocalRecord:
    """Immutable local record entity used by application record services."""

    record_id: str
    source_identity: str
    canonical_name: str
    sync_status: SyncStatus
    processing_status: RecordProcessingStatus
    revision: int
    created_at: datetime
    updated_at: datetime
    last_reason_code: str | None = None
    metadata: Mapping[str, str] | None = None


def _validate_identity(
    *,
    record_id: str,
    source_identity: str,
    canonical_name: str,
) -> None:
    if not record_id:
        raise LocalRecordIdentityError("record_id must be non-empty.")
    if not source_identity:
        raise LocalRecordIdentityError("source_identity must be non-empty.")
    if not canonical_name:
        raise LocalRecordIdentityError("canonical_name must be non-empty.")


def _validate_timestamp_progression(previous: datetime, updated: datetime) -> None:
    if updated < previous:
        raise LocalRecordTimestampError(
            "Mutation timestamp cannot be older than current updated_at timestamp.",
        )


def create_record(
    *,
    record_id: str,
    source_identity: str,
    canonical_name: str,
    created_at: datetime,
    metadata: Mapping[str, str] | None = None,
) -> LocalRecord:
    """Construct immutable record with validated identity and baseline state."""
    _validate_identity(
        record_id=record_id,
        source_identity=source_identity,
        canonical_name=canonical_name,
    )
    return LocalRecord(
        record_id=record_id,
        source_identity=source_identity,
        canonical_name=canonical_name,
        sync_status=SyncStatus.UNSYNCED,
        processing_status=RecordProcessingStatus.PENDING,
        revision=0,
        created_at=created_at,
        updated_at=created_at,
        metadata=dict(metadata or {}),
    )


def apply_processing_result(
    record: LocalRecord,
    *,
    processing_status: RecordProcessingStatus,
    updated_at: datetime,
    reason_code: str | None = None,
) -> LocalRecord:
    """Apply processing status mutation with monotonic revision/timestamp checks."""
    _validate_timestamp_progression(record.updated_at, updated_at)
    return replace(
        record,
        processing_status=processing_status,
        revision=record.revision + 1,
        updated_at=updated_at,
        last_reason_code=reason_code,
    )


def mark_synced(record: LocalRecord, *, updated_at: datetime) -> LocalRecord:
    """Transition record from unsynced to synced with revision increment."""
    if record.sync_status is SyncStatus.SYNCED:
        raise LocalRecordTransitionError("Record is already synced.")
    _validate_timestamp_progression(record.updated_at, updated_at)
    return replace(
        record,
        sync_status=SyncStatus.SYNCED,
        revision=record.revision + 1,
        updated_at=updated_at,
    )


def mark_unsynced(record: LocalRecord, *, updated_at: datetime) -> LocalRecord:
    """Transition record from synced to unsynced with revision increment."""
    if record.sync_status is SyncStatus.UNSYNCED:
        raise LocalRecordTransitionError("Record is already unsynced.")
    _validate_timestamp_progression(record.updated_at, updated_at)
    return replace(
        record,
        sync_status=SyncStatus.UNSYNCED,
        revision=record.revision + 1,
        updated_at=updated_at,
    )


def same_identity(left: LocalRecord, right: LocalRecord) -> bool:
    """Compare identity fields while ignoring revision and mutable statuses."""
    return (
        left.record_id == right.record_id
        and left.source_identity == right.source_identity
        and left.canonical_name == right.canonical_name
    )


def differs_by_revision(left: LocalRecord, right: LocalRecord) -> bool:
    """Return True when identities match but revision values differ."""
    return same_identity(left, right) and left.revision != right.revision
