"""Protocol and error contracts for V2 application adapter boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Generic, Mapping, Protocol, TypeVar, runtime_checkable


class PortError(RuntimeError):
    """Base exception for adapter contract failures crossing port boundaries."""


class PortBindingError(PortError):
    """Raised when composition cannot provide a complete valid binding set."""


class PortResponseContractError(PortError):
    """Raised when an adapter response violates expected contract shape."""


class PortTimeoutError(PortError):
    """Raised when adapter operation exceeds timeout constraints."""


class PortCancelledError(PortError):
    """Raised when adapter operation is cancelled before completion."""


TValue = TypeVar("TValue")


def _as_normalized_token(
    value: object,
    *,
    field_name: str,
    lowercase: bool = False,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PortResponseContractError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if lowercase:
        normalized = normalized.lower()
    return normalized


def _as_optional_token(value: object, *, field_name: str) -> str | None:
    if value is None:
        return None
    return _as_normalized_token(value, field_name=field_name)


@dataclass(frozen=True, slots=True)
class PortResult(Generic[TValue]):
    """Generic result envelope for recoverable adapter interactions."""

    ok: bool
    value: TValue | None = None
    error: PortError | None = None

    def __post_init__(self) -> None:
        if self.ok:
            if self.error is not None:
                raise PortResponseContractError("successful result cannot contain error")
            return
        if self.error is None:
            raise PortResponseContractError("failed result must contain error")

    @classmethod
    def success(cls, *, value: TValue) -> PortResult[TValue]:
        """Build an envelope representing a successful adapter call."""
        return cls(ok=True, value=value, error=None)

    @classmethod
    def failure(cls, *, error: PortError) -> PortResult[TValue]:
        """Build an envelope representing a failed adapter call."""
        return cls(ok=False, value=None, error=error)


@dataclass(frozen=True, slots=True)
class SyncRequest:
    """Request envelope for sync operations crossing the sync boundary."""

    record_id: str | None = None
    payload: Mapping[str, Any] = MappingProxyType({})
    operation: str = "sync"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "record_id",
            _as_optional_token(self.record_id, field_name="record_id"),
        )
        object.__setattr__(
            self,
            "operation",
            _as_normalized_token(self.operation, field_name="operation", lowercase=True),
        )
        if not isinstance(self.payload, Mapping):
            raise PortResponseContractError("payload must be a mapping")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


@dataclass(frozen=True, slots=True)
class SyncResponse:
    """Response envelope produced by sync adapters."""

    status: str
    remote_id: str | None = None
    reason_code: str | None = None
    metadata: Mapping[str, Any] = MappingProxyType({})

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "status",
            _as_normalized_token(self.status, field_name="status", lowercase=True),
        )
        object.__setattr__(
            self,
            "remote_id",
            _as_optional_token(self.remote_id, field_name="remote_id"),
        )
        object.__setattr__(
            self,
            "reason_code",
            _as_optional_token(self.reason_code, field_name="reason_code"),
        )
        if not isinstance(self.metadata, Mapping):
            raise PortResponseContractError("metadata must be a mapping")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@runtime_checkable
class UiPort(Protocol):
    """UI interaction contract consumed by application/runtime orchestration."""

    def initialize(self) -> None:
        """Initialize adapter resources prior to use."""

    def notify(self, *, severity: str, title: str, message: str) -> None:
        """Emit user-visible notifications."""

    def prompt(self, *, prompt_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Request user interaction and return normalized response."""

    def show_status(self, *, message: str) -> None:
        """Emit a status update for runtime progress."""

    def shutdown(self) -> None:
        """Release adapter resources during teardown."""


@runtime_checkable
class EventPort(Protocol):
    """Event sink contract for UI/observability adapters."""

    def emit(self, event: object) -> None:
        """Emit a canonical event payload."""


@runtime_checkable
class RecordStorePort(Protocol):
    """Persistence boundary for record lifecycle operations."""

    def create(self, record: object) -> object:
        """Persist a new record."""

    def update(self, record_id: str, mutation: object) -> object:
        """Apply a record mutation and return updated snapshot."""

    def mark_unsynced(self, record_id: str) -> None:
        """Mark record as requiring sync retry."""

    def save(self, record: object) -> object:
        """Persist record snapshot and return saved model."""


@runtime_checkable
class FileOpsPort(Protocol):
    """Filesystem side-effect contract used by ingestion runtime services."""

    def read_bytes(self, path: str) -> bytes:
        """Read file bytes from source path."""

    def move(self, source: str, target: str) -> Any:
        """Move source artifact to target location."""

    def exists(self, path: str) -> bool:
        """Probe path existence."""

    def mkdir(self, path: str) -> Any:
        """Create directory path if needed."""

    def delete(self, path: str) -> None:
        """Delete a file or directory according to policy."""


@runtime_checkable
class SyncPort(Protocol):
    """Sync side-effect contract for remote publication operations."""

    def sync_record(self, request: SyncRequest) -> SyncResponse:
        """Synchronize a record payload and return normalized outcome."""


@runtime_checkable
class PluginHostPort(Protocol):
    """Plugin host lookup contract consumed by factory/runtime policies."""

    def get_device_plugins(self) -> tuple[object, ...]:
        """Return registered device plugins."""

    def get_pc_plugins(self) -> tuple[object, ...]:
        """Return registered PC plugins."""

    def get_by_capability(self, capability: str) -> tuple[object, ...]:
        """Return plugins that advertise a required capability."""


@runtime_checkable
class ClockPort(Protocol):
    """Clock provider boundary to keep time sources injectable."""

    def now(self) -> datetime:
        """Return current timestamp in deterministic clock domain."""


@runtime_checkable
class FilesystemPort(Protocol):
    """Path normalization and safety boundary for filesystem policies."""

    def normalize_path(self, value: str) -> str:
        """Normalize input path value to canonical representation."""


_REQUIRED_PORT_PROTOCOLS: Mapping[str, type[Protocol]] = MappingProxyType(
    {
        "ui": UiPort,
        "event": EventPort,
        "record_store": RecordStorePort,
        "file_ops": FileOpsPort,
        "sync": SyncPort,
        "plugin_host": PluginHostPort,
        "clock": ClockPort,
        "filesystem": FilesystemPort,
    }
)


def validate_port_bindings(bindings: Mapping[str, object]) -> Mapping[str, object]:
    """Validate required port bindings and protocol conformance."""
    if not isinstance(bindings, Mapping):
        raise PortBindingError("bindings must be a mapping")

    provided = set(bindings)
    required = set(_REQUIRED_PORT_PROTOCOLS)
    missing = sorted(required - provided)
    if missing:
        raise PortBindingError(f"missing required port bindings: {', '.join(missing)}")

    unknown = sorted(provided - required)
    if unknown:
        raise PortBindingError(f"unknown port bindings: {', '.join(unknown)}")

    for port_name, protocol in _REQUIRED_PORT_PROTOCOLS.items():
        if not isinstance(bindings[port_name], protocol):
            raise PortBindingError(f"binding for '{port_name}' does not match protocol")

    return MappingProxyType(dict(bindings))
