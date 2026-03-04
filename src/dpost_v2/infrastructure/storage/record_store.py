"""SQLite-backed record store adapter for V2 record lifecycle persistence."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


class RecordStoreError(RuntimeError):
    """Base exception for record-store adapter failures."""


class RecordStoreConnectionError(RecordStoreError):
    """Raised when sqlite connection cannot be opened."""


class RecordStoreSchemaError(RecordStoreError):
    """Raised when schema version validation fails."""


class RecordStoreConflictError(RecordStoreError):
    """Raised when optimistic concurrency checks fail."""


class RecordStoreIntegrityError(RecordStoreError):
    """Raised when persistence fails due to integrity constraints."""


class RecordStoreTimeoutError(RecordStoreError):
    """Raised when sqlite reports timeout/lock conditions."""


@dataclass(frozen=True, slots=True)
class RecordStoreConfig:
    """Configuration for sqlite-backed record store adapter."""

    path: str | Path
    timeout_seconds: float = 5.0
    expected_schema_version: int = 1
    auto_migrate: bool = True

    def normalized_path(self) -> Path:
        """Return absolute filesystem path for sqlite database file."""
        return Path(self.path).expanduser().resolve(strict=False)


class SqliteRecordStoreAdapter:
    """RecordStorePort-compatible adapter backed by SQLite."""

    def __init__(self, config: RecordStoreConfig) -> None:
        self._config = config
        self._path = config.normalized_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._connection = sqlite3.connect(
                self._path,
                timeout=float(config.timeout_seconds),
                isolation_level=None,
            )
        except sqlite3.Error as exc:
            raise RecordStoreConnectionError(f"failed to connect: {exc}") from exc

        self._connection.row_factory = sqlite3.Row
        self._ensure_schema()

    def create(self, record: object) -> dict[str, Any]:
        """Insert a new record snapshot."""
        normalized = self._normalize_record_input(record)
        created_at = datetime.now(tz=UTC).isoformat()
        try:
            with self._transaction():
                self._connection.execute(
                    """
                    INSERT INTO records (record_id, revision, payload_json, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        normalized["record_id"],
                        normalized["revision"],
                        json.dumps(normalized["payload"], sort_keys=True),
                        created_at,
                    ),
                )
            return self.get_or_raise(normalized["record_id"])
        except sqlite3.IntegrityError as exc:
            raise RecordStoreConflictError(str(exc)) from exc
        except sqlite3.OperationalError as exc:
            raise self._map_operational_error(exc)

    def save(self, record: object) -> dict[str, Any]:
        """Insert or update record snapshot while preserving monotonic revisions."""
        normalized = self._normalize_record_input(record)
        existing = self.get(normalized["record_id"])
        if existing is None:
            return self.create(normalized)

        if int(normalized["revision"]) <= int(existing["revision"]):
            raise RecordStoreConflictError("incoming revision must be greater than stored revision")

        updated_at = datetime.now(tz=UTC).isoformat()
        try:
            with self._transaction():
                self._connection.execute(
                    """
                    UPDATE records
                    SET revision = ?, payload_json = ?, updated_at = ?
                    WHERE record_id = ?
                    """,
                    (
                        int(normalized["revision"]),
                        json.dumps(normalized["payload"], sort_keys=True),
                        updated_at,
                        normalized["record_id"],
                    ),
                )
            return self.get_or_raise(normalized["record_id"])
        except sqlite3.IntegrityError as exc:
            raise RecordStoreIntegrityError(str(exc)) from exc
        except sqlite3.OperationalError as exc:
            raise self._map_operational_error(exc)

    def update(self, record_id: str, mutation: object) -> dict[str, Any]:
        """Apply mutation with optimistic concurrency check."""
        current = self.get_or_raise(record_id)
        if not isinstance(mutation, Mapping):
            raise RecordStoreConflictError("mutation must be a mapping")
        if "expected_revision" not in mutation:
            raise RecordStoreConflictError("expected_revision is required for update")

        expected_revision = int(mutation["expected_revision"])
        if expected_revision != int(current["revision"]):
            raise RecordStoreConflictError(
                f"revision conflict for record {record_id!r}: expected {expected_revision}, current {current['revision']}"
            )

        patch_payload = mutation.get("payload", {})
        if not isinstance(patch_payload, Mapping):
            raise RecordStoreConflictError("mutation.payload must be a mapping")
        merged_payload = dict(current["payload"])
        merged_payload.update(dict(patch_payload))
        new_revision = int(current["revision"]) + 1
        updated_at = datetime.now(tz=UTC).isoformat()

        try:
            with self._transaction():
                self._connection.execute(
                    """
                    UPDATE records
                    SET revision = ?, payload_json = ?, updated_at = ?
                    WHERE record_id = ? AND revision = ?
                    """,
                    (
                        new_revision,
                        json.dumps(merged_payload, sort_keys=True),
                        updated_at,
                        record_id,
                        expected_revision,
                    ),
                )
            refreshed = self.get_or_raise(record_id)
            if int(refreshed["revision"]) != new_revision:
                raise RecordStoreConflictError("concurrent write detected")
            return refreshed
        except sqlite3.OperationalError as exc:
            raise self._map_operational_error(exc)

    def mark_unsynced(self, record_id: str) -> None:
        """Set sync status to unsynced and bump revision."""
        current = self.get_or_raise(record_id)
        merged_payload = dict(current["payload"])
        merged_payload["sync_status"] = "unsynced"
        self.update(
            record_id,
            {
                "expected_revision": int(current["revision"]),
                "payload": merged_payload,
            },
        )

    def get(self, record_id: str) -> dict[str, Any] | None:
        """Return one record snapshot or None."""
        row = self._connection.execute(
            "SELECT record_id, revision, payload_json, updated_at FROM records WHERE record_id = ?",
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_snapshot(row)

    def get_or_raise(self, record_id: str) -> dict[str, Any]:
        """Return record snapshot or raise conflict when missing."""
        snapshot = self.get(record_id)
        if snapshot is None:
            raise RecordStoreConflictError(f"record not found: {record_id!r}")
        return snapshot

    def healthcheck(self) -> Mapping[str, Any]:
        """Return health and schema diagnostics."""
        row = self._connection.execute(
            "SELECT value FROM metadata WHERE key = 'schema_version'"
        ).fetchone()
        schema_version = int(row["value"]) if row is not None else -1
        return MappingProxyType(
            {
                "status": "ok",
                "path": str(self._path),
                "schema_version": schema_version,
            }
        )

    def close(self) -> None:
        """Close sqlite connection."""
        self._connection.close()

    def _ensure_schema(self) -> None:
        cursor = self._connection.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        row = cursor.execute(
            "SELECT value FROM metadata WHERE key = 'schema_version'"
        ).fetchone()

        expected = self._config.expected_schema_version
        if row is None:
            cursor.execute(
                "INSERT INTO metadata (key, value) VALUES ('schema_version', ?)",
                (str(expected),),
            )
        else:
            current = int(row["value"])
            if current != expected:
                if not self._config.auto_migrate:
                    raise RecordStoreSchemaError(
                        f"schema version mismatch: expected {expected}, got {current}"
                    )
                cursor.execute(
                    "UPDATE metadata SET value = ? WHERE key = 'schema_version'",
                    (str(expected),),
                )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                record_id TEXT PRIMARY KEY,
                revision INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

    @staticmethod
    def _normalize_record_input(record: object) -> dict[str, Any]:
        if not isinstance(record, Mapping):
            raise RecordStoreConflictError("record must be a mapping")
        if "record_id" not in record:
            raise RecordStoreConflictError("record_id is required")

        payload = record.get("payload", {})
        if not isinstance(payload, Mapping):
            raise RecordStoreConflictError("record.payload must be a mapping")

        return {
            "record_id": str(record["record_id"]),
            "revision": int(record.get("revision", 0)),
            "payload": dict(payload),
        }

    @staticmethod
    def _row_to_snapshot(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "record_id": row["record_id"],
            "revision": int(row["revision"]),
            "payload": dict(json.loads(row["payload_json"])),
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _map_operational_error(exc: sqlite3.OperationalError) -> RecordStoreError:
        lowered = str(exc).lower()
        if "locked" in lowered or "busy" in lowered or "timeout" in lowered:
            return RecordStoreTimeoutError(str(exc))
        return RecordStoreIntegrityError(str(exc))

    def _transaction(self):  # type: ignore[no-untyped-def]
        return _Transaction(self._connection)


class _Transaction:
    """Simple transaction context using explicit BEGIN/COMMIT/ROLLBACK."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def __enter__(self) -> "_Transaction":
        self._connection.execute("BEGIN")
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        if exc is None:
            self._connection.execute("COMMIT")
            return False
        self._connection.execute("ROLLBACK")
        return False
