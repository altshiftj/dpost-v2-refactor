"""Contract tests for V2 application port protocols and binding guards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from dpost_v2.application.contracts.events import IngestionSucceeded
from dpost_v2.application.contracts.ports import (
    ClockPort,
    EventPort,
    FileOpsPort,
    FilesystemPort,
    PluginHostPort,
    PortBindingError,
    PortCancelledError,
    PortResponseContractError,
    PortResult,
    PortTimeoutError,
    RecordStorePort,
    SyncPort,
    SyncRequest,
    SyncResponse,
    UiPort,
    validate_port_bindings,
)


@dataclass
class _UiAdapter:
    initialized: bool = False

    def initialize(self) -> None:
        self.initialized = True

    def notify(self, *, severity: str, title: str, message: str) -> None:
        return None

    def prompt(self, *, prompt_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"cancelled": False, "values": payload}

    def show_status(self, *, message: str) -> None:
        return None

    def shutdown(self) -> None:
        self.initialized = False


class _EventAdapter:
    def emit(self, event: object) -> None:
        return None


class _RecordStoreAdapter:
    def create(self, record: object) -> object:
        return record

    def update(self, record_id: str, mutation: object) -> object:
        return mutation

    def mark_unsynced(self, record_id: str) -> None:
        return None

    def save(self, record: object) -> object:
        return record


class _FileOpsAdapter:
    def read_bytes(self, path: str) -> bytes:
        return b""

    def move(self, source: str, target: str) -> Path:
        return Path(target)

    def exists(self, path: str) -> bool:
        return True

    def mkdir(self, path: str) -> Path:
        return Path(path)

    def delete(self, path: str) -> None:
        return None


class _SyncAdapter:
    def sync_record(self, request: SyncRequest) -> SyncResponse:
        return SyncResponse(status="synced")


class _PluginHostAdapter:
    def get_device_plugins(self) -> tuple[object, ...]:
        return ()

    def get_pc_plugins(self) -> tuple[object, ...]:
        return ()

    def get_by_capability(self, capability: str) -> tuple[object, ...]:
        return ()


class _ClockAdapter:
    def now(self) -> datetime:
        return datetime(2026, 3, 4, tzinfo=UTC)


class _FilesystemAdapter:
    def normalize_path(self, value: str) -> str:
        return value


def _valid_bindings() -> dict[str, object]:
    return {
        "ui": _UiAdapter(),
        "event": _EventAdapter(),
        "record_store": _RecordStoreAdapter(),
        "file_ops": _FileOpsAdapter(),
        "sync": _SyncAdapter(),
        "plugin_host": _PluginHostAdapter(),
        "clock": _ClockAdapter(),
        "filesystem": _FilesystemAdapter(),
    }


def test_protocols_are_runtime_checkable_for_mock_adapters() -> None:
    bindings = _valid_bindings()

    assert isinstance(bindings["ui"], UiPort)
    assert isinstance(bindings["event"], EventPort)
    assert isinstance(bindings["record_store"], RecordStorePort)
    assert isinstance(bindings["file_ops"], FileOpsPort)
    assert isinstance(bindings["sync"], SyncPort)
    assert isinstance(bindings["plugin_host"], PluginHostPort)
    assert isinstance(bindings["clock"], ClockPort)
    assert isinstance(bindings["filesystem"], FilesystemPort)


def test_validate_port_bindings_accepts_complete_binding_matrix() -> None:
    bindings = _valid_bindings()

    validated = validate_port_bindings(bindings)

    assert validated["ui"] is bindings["ui"]
    assert validated["sync"] is bindings["sync"]


def test_validate_port_bindings_rejects_missing_required_port() -> None:
    bindings = _valid_bindings()
    bindings.pop("sync")

    with pytest.raises(PortBindingError, match="sync"):
        validate_port_bindings(bindings)


def test_validate_port_bindings_rejects_unknown_binding_name() -> None:
    bindings = _valid_bindings()
    bindings["unknown"] = object()

    with pytest.raises(PortBindingError, match="unknown"):
        validate_port_bindings(bindings)


def test_validate_port_bindings_rejects_non_conformant_binding_object() -> None:
    bindings = _valid_bindings()
    bindings["ui"] = object()

    with pytest.raises(PortBindingError, match="ui"):
        validate_port_bindings(bindings)


def test_validate_port_bindings_rejects_non_mapping_input() -> None:
    with pytest.raises(PortBindingError, match="mapping"):
        validate_port_bindings([])  # type: ignore[arg-type]


def test_validate_port_bindings_returns_immutable_mapping() -> None:
    validated = validate_port_bindings(_valid_bindings())

    with pytest.raises(TypeError):
        validated["ui"] = _UiAdapter()  # type: ignore[index]


def test_sync_envelopes_are_validated_and_payloads_are_immutable() -> None:
    request = SyncRequest(
        record_id="record-1",
        payload={"foo": "bar"},
        operation=" sync ",
    )
    response = SyncResponse(
        status=" synced ",
        metadata={"remote_version": 3},
    )

    assert request.operation == "sync"
    assert response.status == "synced"
    assert request.payload["foo"] == "bar"
    assert response.metadata["remote_version"] == 3

    with pytest.raises(TypeError):
        request.payload["foo"] = "baz"  # type: ignore[index]
    with pytest.raises(TypeError):
        response.metadata["remote_version"] = 4  # type: ignore[index]

    with pytest.raises(PortResponseContractError, match="status"):
        SyncResponse(status=" ")


def test_port_result_helpers_and_port_error_taxonomy() -> None:
    event = IngestionSucceeded(
        event_id="evt-1",
        trace_id="trace-1",
        occurred_at=datetime(2026, 3, 4, tzinfo=UTC),
        payload={},
    )
    ok_result = PortResult.success(value=event)
    failure_result = PortResult.failure(error=PortResponseContractError("bad shape"))

    assert ok_result.ok is True
    assert ok_result.value is event
    assert ok_result.error is None

    assert failure_result.ok is False
    assert failure_result.value is None
    assert isinstance(failure_result.error, PortResponseContractError)
    assert isinstance(PortTimeoutError("timeout"), Exception)
    assert isinstance(PortCancelledError("cancelled"), Exception)
