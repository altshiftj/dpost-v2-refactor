"""Application-level records lifecycle service over the record store port."""

from __future__ import annotations

from datetime import datetime
from types import MappingProxyType
from typing import Callable, Mapping, cast

from dpost_v2.application.contracts.ports import RecordStorePort
from dpost_v2.domain.records.local_record import (
    LocalRecord,
    RecordProcessingStatus,
    SyncStatus,
)


class RecordsServiceError(RuntimeError):
    """Base records-service error."""


class RecordNotFoundError(RecordsServiceError):
    """Raised when a record id does not exist in persistence."""


class RecordValidationError(RecordsServiceError):
    """Raised when a record payload violates service-level constraints."""


class RecordConflictError(RecordsServiceError):
    """Raised when persistence detects an optimistic-concurrency conflict."""


class RecordStoreError(RecordsServiceError):
    """Raised when persistence fails for non-validation, non-conflict reasons."""


class RecordsService:
    """Application service for deterministic record lifecycle operations."""

    def __init__(self, record_store: RecordStorePort) -> None:
        self._record_store = record_store

    def create(self, record: LocalRecord) -> LocalRecord:
        """Persist a newly created local record snapshot."""
        prepared = _to_store_payload(record)
        snapshot = self._store_call(self._record_store.create, prepared)
        return _from_store_snapshot(snapshot)

    def update(self, record_id: str, mutation: Mapping[str, object]) -> LocalRecord:
        """Apply one record mutation and return the updated immutable snapshot."""
        if not isinstance(record_id, str) or not record_id.strip():
            raise RecordValidationError("record_id must be a non-empty string")
        if not isinstance(mutation, Mapping):
            raise RecordValidationError("mutation must be a mapping")
        snapshot = self._store_call(
            self._record_store.update,
            record_id.strip(),
            dict(mutation),
        )
        return _from_store_snapshot(snapshot)

    def mark_unsynced(self, record_id: str) -> LocalRecord:
        """Mark one record unsynced, returning the resulting record snapshot."""
        current = self._get_snapshot(record_id)
        current_local = _from_store_snapshot(current)
        if current_local.sync_status is SyncStatus.UNSYNCED:
            return current_local
        self._store_call(self._record_store.mark_unsynced, record_id)
        refreshed = self._get_snapshot(record_id)
        return _from_store_snapshot(refreshed)

    def save(self, record: LocalRecord) -> LocalRecord:
        """Persist one explicit record snapshot through the record store."""
        prepared = _to_store_payload(record)
        snapshot = self._store_call(self._record_store.save, prepared)
        return _from_store_snapshot(snapshot)

    def _get_snapshot(self, record_id: str) -> Mapping[str, object]:
        if not isinstance(record_id, str) or not record_id.strip():
            raise RecordValidationError("record_id must be a non-empty string")

        getter = getattr(self._record_store, "get_or_raise", None)
        if callable(getter):
            snapshot = self._store_call(cast(Callable[[str], object], getter), record_id)
            return _ensure_snapshot_mapping(snapshot)

        maybe_getter = getattr(self._record_store, "get", None)
        if callable(maybe_getter):
            snapshot = self._store_call(
                cast(Callable[[str], object], maybe_getter),
                record_id,
            )
            if snapshot is None:
                raise RecordNotFoundError(f"record not found: {record_id!r}")
            return _ensure_snapshot_mapping(snapshot)

        raise RecordStoreError(
            "record store must expose get_or_raise(record_id) or get(record_id)"
        )

    def _store_call(self, func: Callable[..., object], *args: object) -> object:
        try:
            return func(*args)
        except RecordsServiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _map_store_exception(exc) from exc


def _to_store_payload(record: LocalRecord) -> Mapping[str, object]:
    if not isinstance(record, LocalRecord):
        raise RecordValidationError("record must be LocalRecord")
    payload: Mapping[str, object] = MappingProxyType(
        {
            "source_identity": record.source_identity,
            "canonical_name": record.canonical_name,
            "sync_status": record.sync_status.value,
            "processing_status": record.processing_status.value,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
            "last_reason_code": record.last_reason_code,
            "metadata": dict(record.metadata or {}),
        }
    )
    return MappingProxyType(
        {
            "record_id": record.record_id,
            "revision": record.revision,
            "payload": payload,
        }
    )


def _from_store_snapshot(snapshot: object) -> LocalRecord:
    mapped = _ensure_snapshot_mapping(snapshot)
    record_id = _require_token(mapped.get("record_id"), field_name="record_id")
    revision = _require_int(mapped.get("revision"), field_name="revision")
    payload = _require_mapping(mapped.get("payload"), field_name="payload")

    created_at = _require_datetime(payload.get("created_at"), field_name="created_at")
    updated_source = mapped.get("updated_at", payload.get("updated_at"))
    updated_at = _require_datetime(updated_source, field_name="updated_at")

    sync_status = _require_enum(
        payload.get("sync_status"),
        enum_cls=SyncStatus,
        field_name="sync_status",
    )
    processing_status = _require_enum(
        payload.get("processing_status"),
        enum_cls=RecordProcessingStatus,
        field_name="processing_status",
    )

    metadata_raw = payload.get("metadata", {})
    metadata_map = _require_mapping(metadata_raw, field_name="metadata")
    metadata: dict[str, str] = {
        _require_token(key, field_name="metadata key"): _require_token(
            value,
            field_name=f"metadata[{key}]",
        )
        for key, value in metadata_map.items()
    }

    reason_raw = payload.get("last_reason_code")
    reason = None if reason_raw is None else _require_token(reason_raw, field_name="last_reason_code")

    return LocalRecord(
        record_id=record_id,
        source_identity=_require_token(
            payload.get("source_identity"),
            field_name="source_identity",
        ),
        canonical_name=_require_token(
            payload.get("canonical_name"),
            field_name="canonical_name",
        ),
        sync_status=sync_status,
        processing_status=processing_status,
        revision=revision,
        created_at=created_at,
        updated_at=updated_at,
        last_reason_code=reason,
        metadata=metadata,
    )


def _map_store_exception(exc: Exception) -> RecordsServiceError:
    error_name = type(exc).__name__.lower()
    message = str(exc).strip()
    lowered = message.lower()

    if "not found" in lowered:
        return RecordNotFoundError(message)
    if "conflict" in error_name or "conflict" in lowered:
        if "not found" in lowered:
            return RecordNotFoundError(message)
        return RecordConflictError(message)
    if "validation" in error_name:
        return RecordValidationError(message)
    if isinstance(exc, (TypeError, ValueError)):
        return RecordValidationError(message)
    return RecordStoreError(message or type(exc).__name__)


def _ensure_snapshot_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RecordValidationError("record store snapshot must be a mapping")
    return cast(Mapping[str, object], value)


def _require_mapping(value: object, *, field_name: str) -> Mapping[object, object]:
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{field_name} must be a mapping")
    return value


def _require_token(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RecordValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_int(value: object, *, field_name: str) -> int:
    if not isinstance(value, int):
        raise RecordValidationError(f"{field_name} must be an int")
    return value


def _require_datetime(value: object, *, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise RecordValidationError(
            f"{field_name} must be datetime or ISO-8601 datetime string",
        )
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise RecordValidationError(
            f"{field_name} must be datetime or ISO-8601 datetime string",
        ) from exc


def _require_enum(
    value: object,
    *,
    enum_cls: type[SyncStatus] | type[RecordProcessingStatus],
    field_name: str,
) -> SyncStatus | RecordProcessingStatus:
    token = _require_token(value, field_name=field_name).lower()
    try:
        return enum_cls(token)
    except ValueError as exc:
        raise RecordValidationError(
            f"{field_name} value {token!r} is not supported",
        ) from exc
