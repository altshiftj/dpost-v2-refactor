"""Runtime composition root for V2 startup context wiring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Sequence

from dpost_v2.application.contracts.ports import (
    PortBindingError,
    SyncRequest,
    SyncResponse,
    validate_port_bindings,
)
from dpost_v2.application.ingestion.engine import IngestionOutcome, IngestionOutcomeKind
from dpost_v2.application.runtime.dpost_app import DPostApp
from dpost_v2.application.session.session_manager import SessionManager, SessionPolicy
from dpost_v2.application.startup.context import StartupContext

DEFAULT_REQUIRED_PORTS: tuple[str, ...] = (
    "observability",
    "storage",
    "filesystem",
    "clock",
    "sync",
    "ui",
    "event_sink",
    "plugins",
)


class CompositionError(RuntimeError):
    """Base type for composition failures."""


class CompositionBindingError(CompositionError):
    """Raised when required port bindings are missing."""


class CompositionInitializationError(CompositionError):
    """Raised when adapter/app initialization fails."""


class CompositionDuplicateBindingError(CompositionError):
    """Raised when composition attempts to bind a port more than once."""


class CompositionPluginBindingError(CompositionError):
    """Raised when plugin host binding is invalid for runtime composition."""


@dataclass(frozen=True)
class CompositionBundle:
    """Fully wired runtime application bundle."""

    app: Any
    port_bindings: Mapping[str, object]
    diagnostics: Mapping[str, Any]
    shutdown_all: Callable[[], None]

    def __post_init__(self) -> None:
        object.__setattr__(self, "port_bindings", MappingProxyType(dict(self.port_bindings)))
        object.__setattr__(self, "diagnostics", MappingProxyType(dict(self.diagnostics)))


def compose_runtime(
    context: StartupContext,
    *,
    required_ports: Sequence[str] = DEFAULT_REQUIRED_PORTS,
    app_factory: Callable[[Mapping[str, object], StartupContext], Any] | None = None,
    healthchecks: Sequence[Callable[[Mapping[str, object]], None]] = (),
) -> CompositionBundle:
    """Compose adapters and return a runnable runtime bundle."""
    normalized_ports = tuple(required_ports)
    _validate_no_duplicate_ports(normalized_ports)
    _validate_required_bindings(context.dependencies.factories, normalized_ports)
    ordered_ports = _deterministic_port_order(normalized_ports)

    bindings = _instantiate_bindings(context.dependencies.factories, ordered_ports)
    _validate_plugin_binding(bindings.get("plugins"))
    _run_healthchecks(bindings, healthchecks)
    application_ports: Mapping[str, object] | None = None
    if app_factory is None:
        application_ports = _build_application_ports(bindings, context)

    try:
        app = (
            app_factory(bindings, context)
            if app_factory is not None
            else _default_app_factory(bindings, context, application_ports)
        )
    except Exception as exc:
        raise CompositionInitializationError("Failed to build runtime app.") from exc

    app_port_names = (
        tuple(sorted(application_ports))
        if application_ports is not None
        else ()
    )
    return CompositionBundle(
        app=app,
        port_bindings=bindings,
        diagnostics={
            "mode": context.launch.requested_mode,
            "profile": context.launch.requested_profile,
            "required_ports": ordered_ports,
            "selected_backends": dict(context.dependencies.selected_backends),
            "warnings": tuple(context.dependencies.warnings),
            "application_ports": app_port_names,
        },
        shutdown_all=_build_shutdown_hook(bindings),
    )


def _validate_no_duplicate_ports(required_ports: Sequence[str]) -> None:
    seen: set[str] = set()
    for port in required_ports:
        if port in seen:
            raise CompositionDuplicateBindingError(
                f"Duplicate port binding requested for {port!r}."
            )
        seen.add(port)


def _validate_required_bindings(
    factories: Mapping[str, Callable[[], object]],
    required_ports: Sequence[str],
) -> None:
    for port in required_ports:
        if port not in factories:
            raise CompositionBindingError(f"Missing required port binding: {port!r}.")


def _deterministic_port_order(required_ports: Sequence[str]) -> tuple[str, ...]:
    priority = {
        "observability": 0,
        "storage": 1,
        "filesystem": 2,
        "clock": 3,
        "sync": 4,
        "ui": 5,
        "event_sink": 6,
        "plugins": 7,
    }
    return tuple(
        sorted(
            required_ports,
            key=lambda name: (priority.get(name, 100), name),
        )
    )


def _instantiate_bindings(
    factories: Mapping[str, Callable[[], object]],
    required_ports: Sequence[str],
) -> dict[str, object]:
    bindings: dict[str, object] = {}
    for port in required_ports:
        factory = factories[port]
        try:
            bindings[port] = factory()
        except Exception as exc:
            raise CompositionInitializationError(
                f"Failed to initialize adapter for port {port!r}."
            ) from exc
    return bindings


def _run_healthchecks(
    bindings: Mapping[str, object],
    healthchecks: Sequence[Callable[[Mapping[str, object]], None]],
) -> None:
    for healthcheck in healthchecks:
        try:
            healthcheck(bindings)
        except Exception as exc:
            raise CompositionInitializationError(
                "Composition healthcheck failed."
            ) from exc


def _validate_plugin_binding(plugin_binding: object | None) -> None:
    if plugin_binding is None:
        raise CompositionPluginBindingError(
            "Missing plugin host binding for required 'plugins' port."
        )


def _default_app_factory(
    bindings: Mapping[str, object],
    context: StartupContext,
    application_ports: Mapping[str, object] | None,
) -> DPostApp:
    if application_ports is None:
        raise CompositionBindingError("Application ports are unavailable for runtime app.")

    event_port = application_ports["event"]
    event_emitter = getattr(event_port, "emit")
    clock = application_ports["clock"]
    ui_port = application_ports["ui"]

    session_manager = SessionManager(
        policy=_default_session_policy(context),
        clock=clock,
    )
    session_id = f"session-{context.launch.trace_id}"
    return DPostApp(
        session_manager=session_manager,
        ingestion_engine=_NoopIngestionEngine(),
        event_source=_resolve_event_source(ui_port),
        event_emitter=event_emitter,
        clock=clock,
        session_id=session_id,
        trace_id=context.launch.trace_id,
        mode=context.launch.requested_mode,
        profile=context.settings.profile or "default",
        dependency_ids={
            "clock": f"clock:{context.dependencies.selected_backends.get('observability', 'default')}",
            "ui": f"ui:{context.dependencies.selected_backends.get('ui', 'default')}",
            "sync": f"sync:{context.dependencies.selected_backends.get('sync', 'default')}",
        },
        settings_snapshot={
            "mode": context.settings.mode,
            "profile": context.settings.profile or "default",
        },
    )


def _build_shutdown_hook(bindings: Mapping[str, object]) -> Callable[[], None]:
    hooks: list[Callable[[], None]] = []
    for adapter in bindings.values():
        shutdown = _extract_shutdown_hook(adapter)
        if shutdown is not None:
            hooks.append(shutdown)

    def shutdown_all() -> None:
        for hook in reversed(hooks):
            hook()

    return shutdown_all


def _extract_shutdown_hook(adapter: object) -> Callable[[], None] | None:
    for attr_name in ("shutdown", "close", "stop"):
        candidate = getattr(adapter, attr_name, None)
        if callable(candidate):
            return candidate
    return None


def _default_session_policy(context: StartupContext) -> SessionPolicy:
    idle_timeout = _extract_optional_timeout(context.settings, "idle_timeout_seconds")
    max_runtime = _extract_optional_timeout(context.settings, "max_runtime_seconds")
    return SessionPolicy(
        idle_timeout_seconds=idle_timeout,
        max_runtime_seconds=max_runtime,
    )


def _extract_optional_timeout(settings: object, field_name: str) -> float | None:
    runtime_block = getattr(settings, "runtime", None)
    candidate = getattr(runtime_block, field_name, None)
    if candidate is None:
        candidate = getattr(settings, field_name, None)
    if candidate is None:
        return None
    return float(candidate)


def _resolve_clock_binding(
    bindings: Mapping[str, object],
    context: StartupContext,
) -> "_ClockPort":
    candidate = bindings.get("clock")
    if candidate is None:
        clock_factory = context.dependencies.factories.get("clock")
        if clock_factory is not None:
            candidate = clock_factory()
    if candidate is None:
        raise CompositionBindingError("Missing required clock binding for runtime app.")
    if _is_clock_port(candidate):
        return candidate
    if isinstance(candidate, Mapping) and candidate.get("kind") == "clock":
        return _SystemClock()
    raise CompositionBindingError("binding for 'clock' does not match protocol")


def _build_application_ports(
    bindings: Mapping[str, object],
    context: StartupContext,
) -> Mapping[str, object]:
    event_sink_binding = bindings.get("event_sink")
    storage_binding = bindings.get("storage")
    filesystem_binding = bindings.get("filesystem")
    sync_binding = bindings.get("sync")
    ui_binding = bindings.get("ui")
    plugin_binding = bindings.get("plugins")
    if event_sink_binding is None:
        raise CompositionBindingError("Missing required port binding: 'event_sink'.")
    if storage_binding is None:
        raise CompositionBindingError("Missing required port binding: 'storage'.")
    if filesystem_binding is None:
        raise CompositionBindingError("Missing required port binding: 'filesystem'.")
    if sync_binding is None:
        raise CompositionBindingError("Missing required port binding: 'sync'.")
    if ui_binding is None:
        raise CompositionBindingError("Missing required port binding: 'ui'.")
    if plugin_binding is None:
        raise CompositionBindingError("Missing required port binding: 'plugins'.")

    app_bindings = {
        "ui": _coerce_ui_port(ui_binding),
        "event": _coerce_event_port(event_sink_binding),
        "record_store": _coerce_record_store_port(storage_binding),
        "file_ops": _coerce_file_ops_port(filesystem_binding),
        "sync": _coerce_sync_port(sync_binding),
        "plugin_host": _coerce_plugin_host_port(plugin_binding),
        "clock": _resolve_clock_binding(bindings, context),
        "filesystem": _coerce_filesystem_port(filesystem_binding),
    }
    try:
        return validate_port_bindings(app_bindings)
    except PortBindingError as exc:
        raise CompositionBindingError(str(exc)) from exc


def _coerce_ui_port(binding: object) -> object:
    required_methods = ("initialize", "notify", "prompt", "show_status", "shutdown")
    if all(callable(getattr(binding, method, None)) for method in required_methods):
        return binding
    if isinstance(binding, Mapping) and binding.get("kind") == "ui":
        return _UiAdapter(backend=str(binding.get("backend", "headless")))
    raise CompositionBindingError("binding for 'ui' does not match protocol")


def _coerce_event_port(binding: object) -> object:
    emit = getattr(binding, "emit", None)
    if callable(emit):
        return binding
    if callable(binding):
        return _CallableEventAdapter(binding)
    if isinstance(binding, Mapping) and binding.get("kind") == "event_sink":
        return _EventAdapter()
    raise CompositionBindingError("binding for 'event' does not match protocol")


def _coerce_record_store_port(binding: object) -> object:
    required_methods = ("create", "update", "mark_unsynced", "save")
    if all(callable(getattr(binding, method, None)) for method in required_methods):
        return binding
    if isinstance(binding, Mapping) and binding.get("kind") == "storage":
        return _InMemoryRecordStore()
    raise CompositionBindingError("binding for 'record_store' does not match protocol")


def _coerce_file_ops_port(binding: object) -> object:
    required_methods = ("read_bytes", "move", "exists", "mkdir", "delete")
    if all(callable(getattr(binding, method, None)) for method in required_methods):
        return binding
    if isinstance(binding, Mapping) and binding.get("kind") == "filesystem":
        return _FileOpsAdapter()
    raise CompositionBindingError("binding for 'file_ops' does not match protocol")


def _coerce_sync_port(binding: object) -> object:
    if callable(getattr(binding, "sync_record", None)):
        return binding
    if isinstance(binding, Mapping) and binding.get("kind") == "sync":
        return _SyncAdapter(backend=str(binding.get("backend", "noop")))
    raise CompositionBindingError("binding for 'sync' does not match protocol")


def _coerce_plugin_host_port(binding: object) -> object:
    required_methods = ("get_device_plugins", "get_pc_plugins", "get_by_capability")
    if all(callable(getattr(binding, method, None)) for method in required_methods):
        return binding
    if isinstance(binding, Mapping) and binding.get("kind") == "plugins":
        return _PluginHostAdapter()
    raise CompositionBindingError("binding for 'plugin_host' does not match protocol")


def _coerce_filesystem_port(binding: object) -> object:
    if callable(getattr(binding, "normalize_path", None)):
        return binding
    if isinstance(binding, Mapping) and binding.get("kind") == "filesystem":
        return _FilesystemAdapter()
    raise CompositionBindingError("binding for 'filesystem' does not match protocol")


def _resolve_event_source(ui_port: object) -> Iterable[Mapping[str, Any]]:
    candidate = getattr(ui_port, "iter_events", None)
    if callable(candidate):
        source = candidate()
        if isinstance(source, Iterable):
            return source
    return ()


class _ClockPort:
    def now(self) -> datetime:  # pragma: no cover - protocol-like marker
        raise NotImplementedError


def _is_clock_port(value: object) -> bool:
    return callable(getattr(value, "now", None))


class _SystemClock(_ClockPort):
    def now(self) -> datetime:
        return datetime.now(UTC)


class _NoopIngestionEngine:
    def process(
        self,
        *,
        event: Mapping[str, Any],
        processing_context: Any | None = None,
    ) -> IngestionOutcome[object]:
        return IngestionOutcome(
            kind=IngestionOutcomeKind.SUCCEEDED,
            final_stage_id=None,
            state={
                "event_id": event.get("event_id"),
                "processing_context_event_id": getattr(
                    processing_context,
                    "event_id",
                    None,
                ),
            },
            stage_trace=(),
            retry_plan=None,
            emission_status="skipped",
        )


class _UiAdapter:
    def __init__(self, *, backend: str) -> None:
        self.backend = backend

    def initialize(self) -> None:
        return None

    def notify(self, *, severity: str, title: str, message: str) -> None:
        return None

    def prompt(self, *, prompt_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"prompt_type": prompt_type, "payload": dict(payload), "accepted": True}

    def show_status(self, *, message: str) -> None:
        return None

    def shutdown(self) -> None:
        return None


class _EventAdapter:
    def emit(self, event: object) -> None:
        return None


class _CallableEventAdapter:
    def __init__(self, emit_fn: Callable[[Mapping[str, Any]], None]) -> None:
        self._emit_fn = emit_fn

    def emit(self, event: object) -> None:
        if isinstance(event, Mapping):
            self._emit_fn(event)
            return
        self._emit_fn({"event": event})


class _InMemoryRecordStore:
    def __init__(self) -> None:
        self._records: dict[str, object] = {}

    def create(self, record: object) -> object:
        record_id = f"record-{len(self._records) + 1}"
        self._records[record_id] = record
        return record

    def update(self, record_id: str, mutation: object) -> object:
        self._records[record_id] = mutation
        return mutation

    def mark_unsynced(self, record_id: str) -> None:
        return None

    def save(self, record: object) -> object:
        record_id = f"record-{len(self._records) + 1}"
        self._records[record_id] = record
        return record


class _FileOpsAdapter:
    def read_bytes(self, path: str) -> bytes:
        return str(path).encode("utf-8")

    def move(self, source: str, target: str) -> str:
        return str(PurePath(target))

    def exists(self, path: str) -> bool:
        return True

    def mkdir(self, path: str) -> str:
        return str(PurePath(path))

    def delete(self, path: str) -> None:
        return None


class _SyncAdapter:
    def __init__(self, *, backend: str) -> None:
        self._backend = backend

    def sync_record(self, request: SyncRequest) -> SyncResponse:
        if self._backend == "noop":
            return SyncResponse(status="synced", metadata={"backend": "noop"})
        return SyncResponse(status="synced", metadata={"backend": self._backend})


class _PluginHostAdapter:
    def get_device_plugins(self) -> tuple[object, ...]:
        return ()

    def get_pc_plugins(self) -> tuple[object, ...]:
        return ()

    def get_by_capability(self, capability: str) -> tuple[object, ...]:
        return ()


class _FilesystemAdapter:
    def normalize_path(self, value: str) -> str:
        return str(PurePath(value))
