"""Kadi sync adapter implementation with normalized SyncPort outcomes."""

from __future__ import annotations

import hashlib
import json
from types import MappingProxyType
from typing import Any, Callable, Mapping

from dpost_v2.application.contracts.ports import SyncRequest, SyncResponse

KadiClient = Callable[..., Mapping[str, Any]]


class KadiSyncError(RuntimeError):
    """Base error for Kadi sync adapter failures."""


class KadiSyncAuthError(KadiSyncError):
    """Raised when Kadi credentials are rejected."""


class KadiSyncNetworkError(KadiSyncError):
    """Raised for timeout/connectivity failures."""


class KadiSyncConflictError(KadiSyncError):
    """Raised when remote conflict cannot be normalized."""


class KadiSyncResponseError(KadiSyncError):
    """Raised when Kadi response payload shape is invalid."""


class KadiSyncLifecycleError(KadiSyncError):
    """Raised when adapter is used before initialization."""


class KadiSyncAdapter:
    """SyncPort adapter using injected Kadi transport client."""

    def __init__(
        self,
        *,
        endpoint: str,
        api_token: str,
        workspace_id: str,
        client: KadiClient,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._endpoint = endpoint.strip()
        self._api_token = api_token.strip()
        self._workspace_id = workspace_id.strip()
        self._client = client
        self._timeout = float(timeout_seconds)
        self._ready = False

    def initialize(self) -> None:
        """Validate base configuration and activate adapter lifecycle."""
        if not self._endpoint:
            raise KadiSyncResponseError("endpoint must be non-empty")
        if not self._workspace_id:
            raise KadiSyncResponseError("workspace_id must be non-empty")
        if not self._api_token:
            raise KadiSyncAuthError("api_token must be non-empty")
        self._ready = True

    def shutdown(self) -> None:
        """Deactivate adapter lifecycle."""
        self._ready = False

    def healthcheck(self) -> Mapping[str, Any]:
        """Return simple readiness diagnostics."""
        return MappingProxyType(
            {
                "adapter": "kadi_sync",
                "endpoint": self._endpoint,
                "workspace_id": self._workspace_id,
                "ready": self._ready,
            }
        )

    def sync_record(self, request: SyncRequest) -> SyncResponse:
        """Execute Kadi sync call and normalize transport outcome."""
        if not self._ready:
            raise KadiSyncLifecycleError("kadi sync adapter is not initialized")
        if not isinstance(request, SyncRequest):
            raise KadiSyncResponseError("request must be SyncRequest")
        if request.record_id is None:
            raise KadiSyncResponseError("request.record_id must be provided")

        payload = self._serialize_payload(request)
        headers = self._build_headers(request)

        try:
            raw_response = self._client(
                payload=payload,
                headers=headers,
                timeout=self._timeout,
            )
        except TimeoutError as exc:
            raise KadiSyncNetworkError("kadi sync timed out") from exc
        except OSError as exc:
            raise KadiSyncNetworkError(str(exc)) from exc

        return self._normalize_response(raw_response)

    def _serialize_payload(self, request: SyncRequest) -> dict[str, Any]:
        return {
            "endpoint": self._endpoint,
            "workspace_id": self._workspace_id,
            "record_id": request.record_id,
            "operation": request.operation,
            "payload": dict(request.payload),
        }

    def _build_headers(self, request: SyncRequest) -> dict[str, str]:
        idempotency_key = request.payload.get("idempotency_key")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            idempotency_key = self._derive_idempotency_key(request)
        return {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }

    @staticmethod
    def _derive_idempotency_key(request: SyncRequest) -> str:
        fingerprint = json.dumps(
            {
                "record_id": request.record_id,
                "operation": request.operation,
                "payload": dict(request.payload),
            },
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(fingerprint).hexdigest()

    def _normalize_response(self, response: Mapping[str, Any]) -> SyncResponse:
        if not isinstance(response, Mapping):
            raise KadiSyncResponseError("response must be a mapping")
        status_code = response.get("status_code")
        if not isinstance(status_code, int):
            raise KadiSyncResponseError("response.status_code must be an integer")

        if status_code in {200, 201}:
            metadata = {
                "status_code": status_code,
            }
            if "remote_version" in response:
                metadata["remote_version"] = response["remote_version"]
            return SyncResponse(
                status="synced",
                remote_id=_as_optional_string(response.get("remote_id")),
                metadata=metadata,
            )
        if status_code == 202:
            return SyncResponse(
                status="queued",
                remote_id=_as_optional_string(response.get("remote_id")),
                metadata={"status_code": status_code},
            )
        if status_code == 409:
            reason = _as_optional_string(response.get("reason_code")) or "conflict"
            return SyncResponse(
                status="conflict",
                remote_id=_as_optional_string(response.get("remote_id")),
                reason_code=reason,
                metadata={"status_code": status_code},
            )
        if status_code in {401, 403}:
            raise KadiSyncAuthError(
                _as_optional_string(response.get("error")) or "authentication failure"
            )
        if status_code >= 500:
            raise KadiSyncNetworkError(
                _as_optional_string(response.get("error"))
                or "remote backend unavailable"
            )
        raise KadiSyncResponseError(f"unsupported kadi response status: {status_code}")


def _as_optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
