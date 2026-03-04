from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Mapping, TypeVar


ValueT = TypeVar("ValueT")


class RuntimeServiceError(RuntimeError):
    """Base runtime-services facade error."""


class RuntimeServiceTimeoutError(RuntimeServiceError):
    """Raised when an adapter call times out."""


class RuntimeServiceCancelledError(RuntimeServiceError):
    """Raised when an adapter call is cancelled."""


class RuntimeServiceContractError(RuntimeServiceError):
    """Raised when required adapter bindings are missing or invalid."""


class RuntimeServiceUnexpectedError(RuntimeServiceError):
    """Raised when an adapter call fails unexpectedly."""


class RuntimeCallStatus(StrEnum):
    """Runtime call status classes."""

    SUCCESS = "success"
    DISABLED = "disabled"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RuntimeCallResult:
    """Typed runtime facade response envelope."""

    status: RuntimeCallStatus
    value: Any
    diagnostics: Mapping[str, Any]


class RuntimeServices:
    """Side-effect facade with normalized adapter error translation."""

    def __init__(
        self,
        *,
        file_ops: Mapping[str, Callable[..., Any]] | None = None,
        record_store: Mapping[str, Callable[..., Any]] | None = None,
        sync_port: Mapping[str, Callable[..., Any]] | None = None,
        event_port: Mapping[str, Callable[..., Any]] | None = None,
        clock_port: Callable[[], float] | None = None,
    ) -> None:
        """Initialize runtime service port bindings."""
        self._file_ops = dict(file_ops or {})
        self._record_store = dict(record_store or {})
        self._sync_port = dict(sync_port or {}) if sync_port is not None else None
        self._event_port = dict(event_port or {}) if event_port is not None else None
        self._clock_port = clock_port

    def read_source(self, *, path: str, correlation: Mapping[str, Any]) -> RuntimeCallResult:
        """Read source facts via bound file adapter."""
        func = self._get_required(self._file_ops, "read_source")
        value = self._invoke_adapter(func, path, dict(correlation))
        return RuntimeCallResult(
            status=RuntimeCallStatus.SUCCESS,
            value=value,
            diagnostics={"operation": "read_source"},
        )

    def move_to_target(
        self,
        *,
        source: str,
        target: str,
        correlation: Mapping[str, Any],
    ) -> RuntimeCallResult:
        """Move an artifact to a target path via bound file adapter."""
        func = self._get_required(self._file_ops, "move_to_target")
        value = self._invoke_adapter(func, source, target, dict(correlation))
        return RuntimeCallResult(
            status=RuntimeCallStatus.SUCCESS,
            value=value,
            diagnostics={"operation": "move_to_target"},
        )

    def save_record(
        self,
        *,
        record_payload: Mapping[str, Any],
        correlation: Mapping[str, Any],
    ) -> RuntimeCallResult:
        """Save one record payload via bound record-store adapter."""
        func = self._get_required(self._record_store, "save_record")
        value = self._invoke_adapter(func, dict(record_payload), dict(correlation))
        return RuntimeCallResult(
            status=RuntimeCallStatus.SUCCESS,
            value=value,
            diagnostics={"operation": "save_record"},
        )

    def emit_event(
        self,
        *,
        payload: Mapping[str, Any],
        correlation: Mapping[str, Any],
    ) -> RuntimeCallResult:
        """Emit a structured event via optional event adapter binding."""
        if self._event_port is None:
            return RuntimeCallResult(
                status=RuntimeCallStatus.DISABLED,
                value=None,
                diagnostics={"operation": "emit_event", "reason": "disabled"},
            )

        func = self._get_required(self._event_port, "emit_event")
        value = self._invoke_adapter(func, dict(payload), dict(correlation))
        return RuntimeCallResult(
            status=RuntimeCallStatus.SUCCESS,
            value=value,
            diagnostics={"operation": "emit_event"},
        )

    def trigger_sync(
        self,
        *,
        record_id: str,
        correlation: Mapping[str, Any],
    ) -> RuntimeCallResult:
        """Trigger optional sync adapter behavior for a record id."""
        if self._sync_port is None:
            return RuntimeCallResult(
                status=RuntimeCallStatus.DISABLED,
                value=None,
                diagnostics={"operation": "trigger_sync", "reason": "disabled"},
            )

        func = self._get_required(self._sync_port, "trigger_sync")
        value = self._invoke_adapter(func, record_id, dict(correlation))
        return RuntimeCallResult(
            status=RuntimeCallStatus.SUCCESS,
            value=value,
            diagnostics={"operation": "trigger_sync"},
        )

    def now(self) -> float:
        """Return current wall-clock timestamp from optional clock adapter."""
        if self._clock_port is None:
            import time

            return time.time()
        return float(self._invoke_adapter(self._clock_port))

    @staticmethod
    def _get_required(
        binding: Mapping[str, Callable[..., Any]],
        method_name: str,
    ) -> Callable[..., Any]:
        func = binding.get(method_name)
        if func is None or not callable(func):
            raise RuntimeServiceContractError(
                f"Missing runtime adapter method '{method_name}'."
            )
        return func

    @staticmethod
    def _invoke_adapter(func: Callable[..., ValueT], *args: Any) -> ValueT:
        try:
            return func(*args)
        except TimeoutError as exc:
            raise RuntimeServiceTimeoutError(str(exc)) from exc
        except RuntimeServiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RuntimeServiceUnexpectedError(str(exc)) from exc
