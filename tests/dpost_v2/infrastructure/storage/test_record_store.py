from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from dpost_v2.infrastructure.storage.record_store import (
    RecordStoreConfig,
    RecordStoreConflictError,
    RecordStoreSchemaError,
    SqliteRecordStoreAdapter,
)


def test_record_store_initializes_schema_and_reports_health(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    adapter = SqliteRecordStoreAdapter(RecordStoreConfig(path=db_path))

    health = adapter.healthcheck()

    assert health["status"] == "ok"
    assert health["schema_version"] == 1
    adapter.close()


def test_create_and_update_round_trip_record_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    adapter = SqliteRecordStoreAdapter(RecordStoreConfig(path=db_path))

    created = adapter.create(
        {
            "record_id": "rec-1",
            "revision": 0,
            "payload": {"sync_status": "synced", "value": 10},
        }
    )
    updated = adapter.update(
        "rec-1",
        {
            "expected_revision": 0,
            "payload": {"value": 11},
        },
    )

    assert created["record_id"] == "rec-1"
    assert updated["revision"] == 1
    assert updated["payload"]["value"] == 11
    assert updated["payload"]["sync_status"] == "synced"
    adapter.close()


def test_update_raises_conflict_for_stale_expected_revision(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    adapter = SqliteRecordStoreAdapter(RecordStoreConfig(path=db_path))
    adapter.create(
        {
            "record_id": "rec-1",
            "revision": 0,
            "payload": {"sync_status": "synced"},
        }
    )

    with pytest.raises(RecordStoreConflictError):
        adapter.update(
            "rec-1",
            {
                "expected_revision": 9,
                "payload": {"value": 11},
            },
        )

    adapter.close()


def test_mark_unsynced_mutates_payload_and_revision(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    adapter = SqliteRecordStoreAdapter(RecordStoreConfig(path=db_path))
    adapter.create(
        {
            "record_id": "rec-1",
            "revision": 0,
            "payload": {"sync_status": "synced"},
        }
    )

    adapter.mark_unsynced("rec-1")
    snapshot = adapter.get("rec-1")

    assert snapshot is not None
    assert snapshot["revision"] == 1
    assert snapshot["payload"]["sync_status"] == "unsynced"
    adapter.close()


def test_schema_version_mismatch_raises_typed_error(tmp_path: Path) -> None:
    db_path = tmp_path / "records.sqlite3"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO metadata (key, value) VALUES ('schema_version', '9')")
    conn.commit()
    conn.close()

    with pytest.raises(RecordStoreSchemaError):
        SqliteRecordStoreAdapter(
            RecordStoreConfig(
                path=db_path,
                expected_schema_version=1,
                auto_migrate=False,
            )
        )
