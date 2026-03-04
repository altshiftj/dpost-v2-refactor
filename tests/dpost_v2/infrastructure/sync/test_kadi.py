from __future__ import annotations

from typing import Any

import pytest

from dpost_v2.application.contracts.ports import SyncRequest
from dpost_v2.infrastructure.sync.kadi import (
    KadiSyncAdapter,
    KadiSyncAuthError,
    KadiSyncNetworkError,
    KadiSyncResponseError,
)


def test_kadi_sync_propagates_idempotency_header_and_normalizes_response() -> None:
    captured: dict[str, Any] = {}

    def _client(*, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        captured["payload"] = payload
        captured["headers"] = headers
        captured["timeout"] = timeout
        return {"status_code": 201, "remote_id": "kadi-1", "remote_version": 7}

    adapter = KadiSyncAdapter(
        endpoint="https://kadi.local",
        api_token="token",
        workspace_id="workspace-1",
        client=_client,
    )
    adapter.initialize()

    response = adapter.sync_record(
        SyncRequest(
            record_id="rec-1",
            operation="sync",
            payload={"idempotency_key": "idem-123", "sample": "A"},
        )
    )

    assert captured["headers"]["Idempotency-Key"] == "idem-123"
    assert captured["headers"]["Authorization"].startswith("Bearer ")
    assert response.status == "synced"
    assert response.remote_id == "kadi-1"
    assert response.metadata["remote_version"] == 7


def test_kadi_sync_maps_auth_failures() -> None:
    def _client(*, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        return {"status_code": 401, "error": "bad token"}

    adapter = KadiSyncAdapter(
        endpoint="https://kadi.local",
        api_token="token",
        workspace_id="workspace-1",
        client=_client,
    )
    adapter.initialize()

    with pytest.raises(KadiSyncAuthError):
        adapter.sync_record(SyncRequest(record_id="rec-1", payload={}))


def test_kadi_sync_maps_timeout_to_network_error() -> None:
    def _client(*, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        raise TimeoutError("timed out")

    adapter = KadiSyncAdapter(
        endpoint="https://kadi.local",
        api_token="token",
        workspace_id="workspace-1",
        client=_client,
    )
    adapter.initialize()

    with pytest.raises(KadiSyncNetworkError):
        adapter.sync_record(SyncRequest(record_id="rec-1", payload={}))


def test_kadi_sync_maps_conflict_status_to_contract_response() -> None:
    def _client(*, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        return {
            "status_code": 409,
            "reason_code": "record_conflict",
            "remote_id": "kadi-1",
        }

    adapter = KadiSyncAdapter(
        endpoint="https://kadi.local",
        api_token="token",
        workspace_id="workspace-1",
        client=_client,
    )
    adapter.initialize()

    response = adapter.sync_record(SyncRequest(record_id="rec-1", payload={}))

    assert response.status == "conflict"
    assert response.reason_code == "record_conflict"


def test_kadi_sync_rejects_unexpected_response_shape() -> None:
    def _client(*, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        return {"not_status_code": 1}

    adapter = KadiSyncAdapter(
        endpoint="https://kadi.local",
        api_token="token",
        workspace_id="workspace-1",
        client=_client,
    )
    adapter.initialize()

    with pytest.raises(KadiSyncResponseError):
        adapter.sync_record(SyncRequest(record_id="rec-1", payload={}))


def test_kadi_sync_rejects_request_without_record_id_before_transport_call() -> None:
    transport_called = False

    def _client(*, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        nonlocal transport_called
        transport_called = True
        return {"status_code": 201, "remote_id": "kadi-1"}

    adapter = KadiSyncAdapter(
        endpoint="https://kadi.local",
        api_token="token",
        workspace_id="workspace-1",
        client=_client,
    )
    adapter.initialize()

    with pytest.raises(KadiSyncResponseError):
        adapter.sync_record(SyncRequest(payload={}))

    assert transport_called is False
