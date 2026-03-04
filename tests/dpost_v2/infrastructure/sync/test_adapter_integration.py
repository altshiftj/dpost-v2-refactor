from __future__ import annotations

from typing import Any

import pytest

from dpost_v2.application.contracts.ports import SyncRequest
from dpost_v2.infrastructure.sync.kadi import KadiSyncAdapter, KadiSyncLifecycleError
from dpost_v2.infrastructure.sync.noop import NoopSyncAdapter, NoopSyncLifecycleError


def test_sync_adapters_produce_contract_responses_for_same_request() -> None:
    def _client(
        *, payload: dict[str, Any], headers: dict[str, str], timeout: float
    ) -> dict[str, Any]:
        return {"status_code": 201, "remote_id": "remote-1"}

    request = SyncRequest(record_id="rec-1", operation="sync", payload={"sample": "A"})

    noop = NoopSyncAdapter(reason_code="offline")
    noop.initialize()
    noop_response = noop.sync_record(request)

    kadi = KadiSyncAdapter(
        endpoint="https://kadi.local",
        api_token="token",
        workspace_id="workspace-1",
        client=_client,
    )
    kadi.initialize()
    kadi_response = kadi.sync_record(request)

    assert noop_response.status == "skipped_noop"
    assert kadi_response.status == "synced"
    assert kadi_response.remote_id == "remote-1"


def test_sync_adapters_enforce_lifecycle_after_shutdown() -> None:
    def _client(
        *, payload: dict[str, Any], headers: dict[str, str], timeout: float
    ) -> dict[str, Any]:
        return {"status_code": 201, "remote_id": "remote-1"}

    request = SyncRequest(record_id="rec-1", operation="sync", payload={"sample": "A"})

    noop = NoopSyncAdapter()
    noop.initialize()
    noop.shutdown()
    with pytest.raises(NoopSyncLifecycleError):
        noop.sync_record(request)

    kadi = KadiSyncAdapter(
        endpoint="https://kadi.local",
        api_token="token",
        workspace_id="workspace-1",
        client=_client,
    )
    kadi.initialize()
    kadi.shutdown()
    with pytest.raises(KadiSyncLifecycleError):
        kadi.sync_record(request)
