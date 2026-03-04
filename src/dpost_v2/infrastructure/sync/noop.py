"""No-op sync adapter used for offline and deterministic test execution."""

from __future__ import annotations

import time
from types import MappingProxyType
from typing import Any, Mapping

from dpost_v2.application.contracts.ports import SyncRequest, SyncResponse


class NoopSyncError(RuntimeError):
    """Base error for noop sync adapter failures."""


class NoopSyncInputError(NoopSyncError):
    """Raised when noop sync input payload is malformed."""


class NoopSyncContractError(NoopSyncError):
    """Raised when caller violates SyncPort request contract."""


class NoopSyncCancelledError(NoopSyncError):
    """Raised when simulated cancellation path is triggered."""


class NoopSyncLifecycleError(NoopSyncError):
    """Raised when sync calls are made outside active lifecycle window."""


class NoopSyncAdapter:
    """Deterministic sync backend that performs no remote side effects."""

    def __init__(
        self,
        *,
        reason_code: str = "offline_noop",
        simulate_latency_seconds: float = 0.0,
    ) -> None:
        self._reason_code = str(reason_code).strip() or "offline_noop"
        self._simulate_latency = max(0.0, float(simulate_latency_seconds))
        self._ready = False

    def initialize(self) -> None:
        """Mark adapter ready for sync requests."""
        self._ready = True

    def shutdown(self) -> None:
        """Mark adapter unavailable for further sync requests."""
        self._ready = False

    def healthcheck(self) -> Mapping[str, Any]:
        """Return current lifecycle readiness diagnostics."""
        return MappingProxyType(
            {
                "adapter": "noop_sync",
                "ready": self._ready,
                "reason_code": self._reason_code,
            }
        )

    def sync_record(self, request: SyncRequest) -> SyncResponse:
        """Return deterministic skipped outcome for any valid request."""
        if not self._ready:
            raise NoopSyncLifecycleError("noop sync adapter is not initialized")
        if not isinstance(request, SyncRequest):
            raise NoopSyncContractError("request must be SyncRequest")
        if request.record_id is None:
            raise NoopSyncInputError("request.record_id must be provided")

        if self._simulate_latency > 0:
            time.sleep(self._simulate_latency)
            if request.payload.get("cancelled"):
                raise NoopSyncCancelledError("simulated noop sync cancellation")

        metadata = {
            "mode": "offline",
            "operation": request.operation,
            "record_id": request.record_id,
            "simulate_latency_seconds": self._simulate_latency,
        }
        return SyncResponse(
            status="skipped_noop",
            reason_code=self._reason_code,
            metadata=metadata,
        )
