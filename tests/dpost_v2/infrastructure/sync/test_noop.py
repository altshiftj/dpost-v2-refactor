from __future__ import annotations

import pytest

from dpost_v2.application.contracts.ports import SyncRequest
from dpost_v2.infrastructure.sync.noop import (
    NoopSyncAdapter,
    NoopSyncCancelledError,
    NoopSyncContractError,
    NoopSyncInputError,
    NoopSyncLifecycleError,
)


def test_noop_sync_requires_initialize_before_usage() -> None:
    adapter = NoopSyncAdapter()

    with pytest.raises(NoopSyncLifecycleError):
        adapter.sync_record(SyncRequest(record_id="rec-1", payload={}))


def test_noop_sync_returns_deterministic_skipped_response() -> None:
    adapter = NoopSyncAdapter(reason_code="offline")
    adapter.initialize()

    first = adapter.sync_record(SyncRequest(record_id="rec-1", payload={"a": 1}))
    second = adapter.sync_record(SyncRequest(record_id="rec-1", payload={"a": 1}))

    assert first == second
    assert first.status == "skipped_noop"
    assert first.reason_code == "offline"


def test_noop_sync_rejects_non_contract_input() -> None:
    adapter = NoopSyncAdapter()
    adapter.initialize()

    with pytest.raises(NoopSyncContractError):
        adapter.sync_record(object())  # type: ignore[arg-type]


def test_noop_sync_can_simulate_cancellation() -> None:
    adapter = NoopSyncAdapter(simulate_latency_seconds=0.01)
    adapter.initialize()

    with pytest.raises(NoopSyncCancelledError):
        adapter.sync_record(
            SyncRequest(record_id="rec-1", payload={"cancelled": True})
        )


def test_noop_sync_rejects_request_without_record_id() -> None:
    adapter = NoopSyncAdapter()
    adapter.initialize()

    with pytest.raises(NoopSyncInputError):
        adapter.sync_record(SyncRequest(payload={}))


def test_noop_healthcheck_lifecycle_state_changes() -> None:
    adapter = NoopSyncAdapter()

    assert adapter.healthcheck()["ready"] is False
    adapter.initialize()
    assert adapter.healthcheck()["ready"] is True
    adapter.shutdown()
    assert adapter.healthcheck()["ready"] is False
