from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping

import pytest

from dpost_v2.application.records.service import (
    RecordConflictError,
    RecordNotFoundError,
    RecordsService,
    RecordValidationError,
)
from dpost_v2.domain.records.local_record import (
    LocalRecord,
    RecordProcessingStatus,
    SyncStatus,
    create_record,
    mark_synced,
)


class _ConflictError(RuntimeError):
    pass


class _FakeRecordStore:
    def __init__(self) -> None:
        self.snapshots: dict[str, dict[str, Any]] = {}
        self.create_calls = 0
        self.save_calls = 0
        self.update_calls = 0
        self.mark_unsynced_calls = 0
        self.last_mark_unsynced_id: str | None = None

    def create(self, record: object) -> object:
        self.create_calls += 1
        payload = _as_store_record(record)
        record_id = payload["record_id"]
        if record_id in self.snapshots:
            raise _ConflictError("record conflict")
        snapshot = _store_snapshot_from_payload(payload)
        self.snapshots[record_id] = snapshot
        return _clone_snapshot(snapshot)

    def save(self, record: object) -> object:
        self.save_calls += 1
        payload = _as_store_record(record)
        record_id = payload["record_id"]
        snapshot = _store_snapshot_from_payload(payload)
        self.snapshots[record_id] = snapshot
        return _clone_snapshot(snapshot)

    def update(self, record_id: str, mutation: object) -> object:
        self.update_calls += 1
        if record_id not in self.snapshots:
            raise RuntimeError(f"record not found: {record_id}")
        if not isinstance(mutation, Mapping):
            raise ValueError("mutation must be mapping")

        current = _clone_snapshot(self.snapshots[record_id])
        expected = mutation.get("expected_revision")
        if not isinstance(expected, int):
            raise _ConflictError("conflict expected_revision missing")
        if expected != current["revision"]:
            raise _ConflictError("conflict revision mismatch")

        payload_patch = mutation.get("payload", {})
        if not isinstance(payload_patch, Mapping):
            raise ValueError("mutation.payload must be mapping")
        merged_payload = dict(current["payload"])
        merged_payload.update(dict(payload_patch))
        current["payload"] = merged_payload
        current["revision"] = current["revision"] + 1
        current["updated_at"] = _ts(18).isoformat()
        self.snapshots[record_id] = _clone_snapshot(current)
        return _clone_snapshot(current)

    def mark_unsynced(self, record_id: str) -> None:
        self.mark_unsynced_calls += 1
        self.last_mark_unsynced_id = record_id
        snapshot = self.get_or_raise(record_id)
        if snapshot["payload"].get("sync_status") == "unsynced":
            return
        snapshot["payload"]["sync_status"] = "unsynced"
        snapshot["revision"] = snapshot["revision"] + 1
        snapshot["updated_at"] = _ts(19).isoformat()
        self.snapshots[record_id] = _clone_snapshot(snapshot)

    def get_or_raise(self, record_id: str) -> dict[str, Any]:
        if record_id not in self.snapshots:
            raise RuntimeError(f"record not found: {record_id}")
        return _clone_snapshot(self.snapshots[record_id])


def test_records_service_create_update_save_happy_path() -> None:
    store = _FakeRecordStore()
    service = RecordsService(record_store=store)

    created = service.create(_record(record_id="rec-1"))
    updated = service.update(
        "rec-1",
        {
            "expected_revision": created.revision,
            "payload": {
                "processing_status": "processed",
                "last_reason_code": "ok",
            },
        },
    )
    saved = service.save(updated)

    assert created.record_id == "rec-1"
    assert created.sync_status is SyncStatus.UNSYNCED
    assert updated.processing_status is RecordProcessingStatus.PROCESSED
    assert updated.last_reason_code == "ok"
    assert saved.record_id == "rec-1"
    assert saved.revision == updated.revision


def test_records_service_mark_unsynced_is_idempotent_for_unsynced_record() -> None:
    store = _FakeRecordStore()
    service = RecordsService(record_store=store)
    service.create(_record(record_id="rec-idempotent"))

    first = service.mark_unsynced("rec-idempotent")
    second = service.mark_unsynced("rec-idempotent")

    assert first.sync_status is SyncStatus.UNSYNCED
    assert second.sync_status is SyncStatus.UNSYNCED
    assert second.revision == first.revision


def test_records_service_mark_unsynced_transitions_synced_record() -> None:
    store = _FakeRecordStore()
    service = RecordsService(record_store=store)
    synced_record = _synced_record("rec-synced")
    service.save(synced_record)

    marked = service.mark_unsynced("rec-synced")

    assert marked.sync_status is SyncStatus.UNSYNCED
    assert marked.revision == synced_record.revision + 1


def test_records_service_mark_unsynced_normalizes_record_id_input() -> None:
    store = _FakeRecordStore()
    service = RecordsService(record_store=store)
    service.save(_synced_record("rec-normalized"))

    marked = service.mark_unsynced("  rec-normalized  ")

    assert marked.record_id == "rec-normalized"
    assert marked.sync_status is SyncStatus.UNSYNCED
    assert store.mark_unsynced_calls == 1
    assert store.last_mark_unsynced_id == "rec-normalized"


def test_records_service_maps_missing_record_to_not_found_error() -> None:
    service = RecordsService(record_store=_FakeRecordStore())

    with pytest.raises(RecordNotFoundError):
        service.update("missing", {"expected_revision": 0, "payload": {}})


def test_records_service_maps_conflict_to_record_conflict_error() -> None:
    store = _FakeRecordStore()
    service = RecordsService(record_store=store)
    created = service.create(_record(record_id="rec-conflict"))

    with pytest.raises(RecordConflictError):
        service.update(
            "rec-conflict",
            {"expected_revision": created.revision + 1, "payload": {}},
        )


def test_records_service_rejects_invalid_inputs() -> None:
    service = RecordsService(record_store=_FakeRecordStore())

    with pytest.raises(RecordValidationError):
        service.create("not-a-record")  # type: ignore[arg-type]

    with pytest.raises(RecordValidationError):
        service.update("rec-1", "bad-mutation")  # type: ignore[arg-type]


def test_records_service_create_validates_record_before_store_call() -> None:
    store = _FakeRecordStore()
    service = RecordsService(record_store=store)
    invalid = LocalRecord(
        record_id="",
        source_identity="source-rec-create-validation",
        canonical_name="artifact.csv",
        sync_status=SyncStatus.UNSYNCED,
        processing_status=RecordProcessingStatus.PENDING,
        revision=0,
        created_at=_ts(10),
        updated_at=_ts(10),
        metadata={"batch": "A"},
    )

    with pytest.raises(RecordValidationError):
        service.create(invalid)

    assert store.create_calls == 0


def test_records_service_save_validates_record_before_store_call() -> None:
    store = _FakeRecordStore()
    service = RecordsService(record_store=store)
    invalid = LocalRecord(
        record_id="rec-save-validation",
        source_identity="source-rec-save-validation",
        canonical_name="",
        sync_status=SyncStatus.UNSYNCED,
        processing_status=RecordProcessingStatus.PENDING,
        revision=0,
        created_at=_ts(10),
        updated_at=_ts(10),
        metadata={"batch": "A"},
    )

    with pytest.raises(RecordValidationError):
        service.save(invalid)

    assert store.save_calls == 0


def test_records_service_update_requires_expected_revision_before_store_call() -> None:
    store = _FakeRecordStore()
    service = RecordsService(record_store=store)
    service.create(_record("rec-update-validation"))

    with pytest.raises(RecordValidationError):
        service.update("rec-update-validation", {"payload": {}})

    assert store.update_calls == 0


def test_records_service_update_requires_payload_mapping_before_store_call() -> None:
    store = _FakeRecordStore()
    service = RecordsService(record_store=store)
    service.create(_record("rec-update-payload-validation"))

    with pytest.raises(RecordValidationError):
        service.update(
            "rec-update-payload-validation",
            {"expected_revision": 0, "payload": "invalid"},  # type: ignore[dict-item]
        )

    assert store.update_calls == 0


def _record(record_id: str) -> LocalRecord:
    return create_record(
        record_id=record_id,
        source_identity=f"source-{record_id}",
        canonical_name=f"artifact-{record_id}.csv",
        created_at=_ts(10),
        metadata={"batch": "A"},
    )


def _synced_record(record_id: str) -> LocalRecord:
    pending = _record(record_id)
    return mark_synced(pending, updated_at=_ts(11))


def _as_store_record(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("store payload must be mapping")
    return value


def _store_snapshot_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    record_payload = payload.get("payload", {})
    if not isinstance(record_payload, Mapping):
        raise ValueError("payload must be mapping")
    return {
        "record_id": payload["record_id"],
        "revision": int(payload.get("revision", 0)),
        "payload": dict(record_payload),
        "updated_at": _ts(17).isoformat(),
    }


def _clone_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_id": snapshot["record_id"],
        "revision": int(snapshot["revision"]),
        "payload": dict(snapshot["payload"]),
        "updated_at": snapshot["updated_at"],
    }


def _ts(hour: int) -> datetime:
    return datetime(2026, 3, 4, hour, 0, tzinfo=UTC)
