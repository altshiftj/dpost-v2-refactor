"""Runtime composition root for V2 startup context wiring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path, PurePath
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Sequence

from dpost_v2.application.contracts.context import ProcessingContext, RuntimeContext
from dpost_v2.application.contracts.ports import (
    PortBindingError,
    SyncRequest,
    SyncResponse,
    validate_port_bindings,
)
from dpost_v2.application.ingestion.engine import IngestionEngine, IngestionOutcome
from dpost_v2.application.ingestion.models.candidate import Candidate
from dpost_v2.application.ingestion.processor_factory import (
    ProcessorNotFoundError,
    ProcessorSelection,
    SelectionDescriptor,
)
from dpost_v2.application.ingestion.runtime_services import (
    RuntimeCallResult,
    RuntimeCallStatus,
)
from dpost_v2.application.ingestion.stages.persist import run_persist_stage
from dpost_v2.application.ingestion.stages.pipeline import (
    DEFAULT_INGESTION_TRANSITION_TABLE,
    PipelineRunner,
)
from dpost_v2.application.ingestion.stages.post_persist import run_post_persist_stage
from dpost_v2.application.ingestion.stages.resolve import run_resolve_stage
from dpost_v2.application.ingestion.stages.route import run_route_stage
from dpost_v2.application.ingestion.stages.stabilize import run_stabilize_stage
from dpost_v2.application.ingestion.stages.transform import run_transform_stage
from dpost_v2.application.ingestion.state import IngestionState
from dpost_v2.application.runtime.dpost_app import DPostApp
from dpost_v2.application.runtime.runtime_host import RuntimeHost
from dpost_v2.application.session.session_manager import SessionManager, SessionPolicy
from dpost_v2.application.startup.context import StartupContext
from dpost_v2.application.startup.settings import StartupSettings
from dpost_v2.plugins.host import PluginHostActivationError

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
class _RuntimePluginPolicy:
    selected_pc_plugin: str | None
    scoped_device_plugins: tuple[str, ...]
    pc_scope_applied: bool


@dataclass(frozen=True)
class CompositionBundle:
    """Fully wired runtime application bundle."""

    app: Any
    runtime_handle: Any
    port_bindings: Mapping[str, object]
    diagnostics: Mapping[str, Any]
    shutdown_all: Callable[[], None]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "port_bindings", MappingProxyType(dict(self.port_bindings))
        )
        object.__setattr__(
            self, "diagnostics", MappingProxyType(dict(self.diagnostics))
        )


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
    plugin_policy = _RuntimePluginPolicy(
        selected_pc_plugin=None,
        scoped_device_plugins=(),
        pc_scope_applied=False,
    )
    shutdown_all = _build_shutdown_hook(bindings)
    if app_factory is None:
        application_ports = _build_application_ports(bindings, context)
        plugin_policy = _resolve_runtime_plugin_policy(
            application_ports=application_ports,
            context=context,
        )

    try:
        app = (
            app_factory(bindings, context)
            if app_factory is not None
            else _default_app_factory(
                bindings,
                context,
                application_ports,
                plugin_policy=plugin_policy,
            )
        )
    except Exception as exc:
        raise CompositionInitializationError("Failed to build runtime app.") from exc

    runtime_handle = RuntimeHost(app=app, shutdown_hook=shutdown_all)

    app_port_names = (
        tuple(sorted(application_ports)) if application_ports is not None else ()
    )
    selected_backends = dict(context.dependencies.selected_backends)
    plugin_backend = selected_backends.get("plugins")
    plugin_port_bound = bindings.get("plugins") is not None
    plugin_contract_valid = (
        application_ports is not None and "plugin_host" in application_ports
    )
    return CompositionBundle(
        app=app,
        runtime_handle=runtime_handle,
        port_bindings=bindings,
        diagnostics={
            "requested_mode": context.launch.requested_mode,
            "requested_profile": context.launch.requested_profile,
            "mode": str(
                getattr(context.settings, "mode", context.launch.requested_mode)
            ),
            "profile": getattr(
                context.settings,
                "profile",
                context.launch.requested_profile,
            ),
            "required_ports": ordered_ports,
            "bound_ports": tuple(sorted(bindings)),
            "selected_backends": selected_backends,
            "backend_provenance": _extract_backend_provenance(
                context.dependencies.diagnostics
            ),
            "plugin_backend": plugin_backend,
            "plugin_port_bound": plugin_port_bound,
            "plugin_contract_valid": plugin_contract_valid,
            "plugin_visibility": _resolve_plugin_visibility(
                plugin_port_bound=plugin_port_bound,
                plugin_contract_valid=plugin_contract_valid,
            ),
            "selected_pc_plugin": plugin_policy.selected_pc_plugin,
            "scoped_device_plugins": plugin_policy.scoped_device_plugins,
            "pc_scope_applied": plugin_policy.pc_scope_applied,
            "warnings": tuple(context.dependencies.warnings),
            "application_ports": app_port_names,
        },
        shutdown_all=shutdown_all,
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
    *,
    plugin_policy: _RuntimePluginPolicy,
) -> DPostApp:
    if application_ports is None:
        raise CompositionBindingError(
            "Application ports are unavailable for runtime app."
        )

    event_port = application_ports["event"]
    event_emitter = getattr(event_port, "emit")
    clock = application_ports["clock"]
    ui_port = application_ports["ui"]

    session_manager = SessionManager(
        policy=_default_session_policy(context),
        clock=clock,
    )
    session_id = f"session-{context.launch.trace_id}"
    ingestion_engine = _build_runtime_ingestion_engine(
        application_ports=application_ports,
        context=context,
        event_emitter=event_emitter,
        plugin_policy=plugin_policy,
    )
    return DPostApp(
        session_manager=session_manager,
        ingestion_engine=ingestion_engine,
        event_source=_resolve_event_source(ui_port, context=context, clock=clock),
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
            "selected_pc_plugin": plugin_policy.selected_pc_plugin,
            "scoped_device_plugins": plugin_policy.scoped_device_plugins,
            "runtime_loop_mode": _resolve_runtime_loop_mode(context.settings),
        },
        loop_mode=_resolve_runtime_loop_mode(context.settings),
        poll_interval_seconds=_resolve_runtime_poll_interval_seconds(context.settings),
    )


def _build_shutdown_hook(bindings: Mapping[str, object]) -> Callable[[], None]:
    hooks: list[Callable[[], None]] = []
    seen_hooks: set[int] = set()
    for adapter in bindings.values():
        shutdown = _extract_shutdown_hook(adapter)
        if shutdown is not None:
            hook_id = id(shutdown)
            if hook_id in seen_hooks:
                continue
            seen_hooks.add(hook_id)
            hooks.append(shutdown)

    has_run = False

    def shutdown_all() -> None:
        nonlocal has_run
        if has_run:
            return
        has_run = True
        for hook in reversed(hooks):
            hook()

    return shutdown_all


def _extract_shutdown_hook(adapter: object) -> Callable[[], None] | None:
    for attr_name in ("shutdown", "close", "stop"):
        candidate = getattr(adapter, attr_name, None)
        if callable(candidate):
            return candidate
    return None


def _extract_backend_provenance(
    dependency_diagnostics: Mapping[str, Any],
) -> dict[str, str]:
    raw = dependency_diagnostics.get("backend_provenance")
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def _resolve_plugin_visibility(
    *,
    plugin_port_bound: bool,
    plugin_contract_valid: bool,
) -> str:
    if not plugin_port_bound:
        return "missing"
    if plugin_contract_valid:
        return "bound"
    return "configured"


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


def _resolve_runtime_loop_mode(settings: object) -> str:
    runtime_block = getattr(settings, "runtime", None)
    candidate = getattr(runtime_block, "loop_mode", None)
    if candidate is None:
        candidate = getattr(settings, "loop_mode", None)
    if candidate is None:
        return "oneshot"
    normalized = str(candidate).strip().lower()
    if normalized in {"oneshot", "continuous"}:
        return normalized
    return "oneshot"


def _resolve_runtime_poll_interval_seconds(settings: object) -> float:
    runtime_block = getattr(settings, "runtime", None)
    candidate = getattr(runtime_block, "poll_interval_seconds", None)
    if candidate is None:
        candidate = getattr(settings, "poll_interval_seconds", None)
    if candidate is None:
        return 1.0
    return max(0.0, float(candidate))


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


def _resolve_event_source(
    ui_port: object,
    *,
    context: StartupContext,
    clock: object,
) -> Iterable[Mapping[str, Any]] | Callable[[], Iterable[Mapping[str, Any]]]:
    candidate = getattr(ui_port, "iter_events", None)
    if callable(candidate):
        source = candidate()
        if isinstance(source, Iterable):
            return source

    mode = str(getattr(context.settings, "mode", context.launch.requested_mode)).lower()
    if mode == "headless":
        return lambda: _discover_headless_events(context=context, clock=clock)
    return _discover_headless_events(context=context, clock=clock)


def _discover_headless_events(
    *,
    context: StartupContext,
    clock: object,
) -> tuple[Mapping[str, Any], ...]:
    mode = str(getattr(context.settings, "mode", context.launch.requested_mode)).lower()
    if mode != "headless":
        return ()
    paths = getattr(context.settings, "paths", None)
    watch_path = getattr(paths, "watch", None)
    if not isinstance(watch_path, str) or not watch_path.strip():
        return ()

    incoming_dir = Path(watch_path)
    try:
        if not incoming_dir.exists() or not incoming_dir.is_dir():
            return ()
        files = tuple(
            sorted(
                (path for path in incoming_dir.iterdir() if path.is_file()),
                key=_headless_event_sort_key,
            )
        )
    except OSError:
        return ()

    events: list[Mapping[str, Any]] = []
    for path in files:
        try:
            stat = path.stat()
            observed_at = float(stat.st_mtime)
        except OSError:
            observed_at = _clock_seconds(clock)
        event_id = sha256(
            f"{path.resolve()}|{observed_at}".encode("utf-8")
        ).hexdigest()[:16]
        events.append(
            {
                "event_id": event_id,
                "path": str(path),
                "event_kind": "created",
            }
        )
    return tuple(events)


def _headless_event_sort_key(path: Path) -> tuple[int, str]:
    try:
        modified_at_ns = int(path.stat().st_mtime_ns)
    except OSError:
        modified_at_ns = 0
    return (modified_at_ns, str(path))


def _build_runtime_ingestion_engine(
    *,
    application_ports: Mapping[str, object],
    context: StartupContext,
    event_emitter: Callable[[Mapping[str, Any]], None],
    plugin_policy: _RuntimePluginPolicy,
) -> object:
    plugin_host = application_ports["plugin_host"]
    file_ops = application_ports["file_ops"]
    record_store = application_ports["record_store"]
    sync_port = application_ports["sync"]
    filesystem = application_ports["filesystem"]
    clock = application_ports["clock"]

    gate_state = _ModifiedEventGateState()
    record_revisions: dict[str, int] = {}
    processor_cache: dict[str, object] = {}
    settle_delay_seconds = _resolve_settle_delay_seconds(context.settings)
    route_root = _resolve_route_root(context.settings)
    allowed_roots = (route_root,)

    def fs_facts_provider(path: str) -> Mapping[str, Any]:
        normalized_path = _normalize_path(filesystem, path)
        return _read_runtime_file_facts(normalized_path, clock=clock)

    def processor_selector(candidate: Candidate) -> ProcessorSelection:
        selection = _select_runtime_processor(
            plugin_host=plugin_host,
            candidate=candidate,
            scoped_plugin_ids=plugin_policy.scoped_device_plugins,
            pc_scope_applied=plugin_policy.pc_scope_applied,
            processor_cache=processor_cache,
        )
        return selection

    def modified_event_gate(event_key: str, event_timestamp: float) -> object:
        return gate_state.evaluate(event_key=event_key, event_timestamp=event_timestamp)

    def now_provider() -> float:
        return _clock_seconds(clock)

    def route_selector(_candidate: Candidate) -> str | None:
        return route_root

    def filename_builder(candidate: Candidate) -> str:
        filename = PurePath(candidate.source_path).name
        if filename.strip():
            return filename
        return f"{candidate.identity_token}.dat"

    def move_file(source: str, target: str) -> RuntimeCallResult:
        try:
            value = getattr(file_ops, "move")(source, target)
            return RuntimeCallResult(
                status=RuntimeCallStatus.SUCCESS,
                value=value,
                diagnostics={"operation": "move"},
            )
        except Exception as exc:  # noqa: BLE001
            return RuntimeCallResult(
                status=RuntimeCallStatus.FAILED,
                value=None,
                diagnostics={"reason_code": "move_failed", "error": str(exc)},
            )

    def save_record(record_payload: Mapping[str, Any]) -> RuntimeCallResult:
        try:
            record_id = _resolve_runtime_record_id(record_payload)
            next_revision = record_revisions.get(record_id, -1) + 1
            normalized_payload = {
                "candidate": dict(record_payload.get("candidate", {})),
                "processor_result": dict(record_payload.get("processor_result") or {}),
                "target_path": record_payload.get("target_path"),
                "sync_status": "pending",
            }
            saved = getattr(record_store, "save")(
                {
                    "record_id": record_id,
                    "revision": next_revision,
                    "payload": normalized_payload,
                }
            )
            record_id = _extract_record_id(saved, record_payload=record_payload)
            record_revisions[record_id] = _extract_record_revision(
                saved,
                fallback=next_revision,
            )
            record_snapshot = _extract_runtime_record_snapshot(
                saved,
                record_id=record_id,
                revision=record_revisions[record_id],
                payload=normalized_payload,
            )
            return RuntimeCallResult(
                status=RuntimeCallStatus.SUCCESS,
                value={
                    "record_id": record_id,
                    "revision": record_revisions[record_id],
                    "record_snapshot": record_snapshot,
                },
                diagnostics={"operation": "save_record"},
            )
        except Exception as exc:  # noqa: BLE001
            return RuntimeCallResult(
                status=RuntimeCallStatus.FAILED,
                value=None,
                diagnostics={"reason_code": "record_save_failed", "error": str(exc)},
            )

    def retry_planner(reason: str, attempt: int) -> Mapping[str, Any]:
        _ = attempt
        return {"terminal_type": "stop_retrying", "reason_code": reason}

    def update_bookkeeping(record_id: str, candidate: Any) -> RuntimeCallResult:
        try:
            update = getattr(record_store, "update", None)
            expected_revision = record_revisions.get(record_id)
            if callable(update) and expected_revision is not None:
                updated = update(
                    record_id,
                    {
                        "expected_revision": expected_revision,
                        "payload": {
                            "bookkeeping": "updated",
                            "plugin_id": getattr(candidate, "plugin_id", None),
                            "persisted_path": getattr(
                                candidate, "persisted_path", None
                            ),
                        },
                    },
                )
                record_revisions[record_id] = _extract_record_revision(
                    updated,
                    fallback=expected_revision + 1,
                )
            return RuntimeCallResult(
                status=RuntimeCallStatus.SUCCESS,
                value=True,
                diagnostics={"operation": "update_bookkeeping"},
            )
        except Exception as exc:  # noqa: BLE001
            return RuntimeCallResult(
                status=RuntimeCallStatus.FAILED,
                value=None,
                diagnostics={"reason_code": "bookkeeping_failed", "error": str(exc)},
            )

    def trigger_sync(state: IngestionState) -> RuntimeCallResult:
        record_id = state.record_id
        if not isinstance(record_id, str) or not record_id.strip():
            return RuntimeCallResult(
                status=RuntimeCallStatus.FAILED,
                value=None,
                diagnostics={"reason_code": "sync_failed"},
            )
        try:
            request_payload = _build_runtime_sync_payload(
                state,
                record_store=record_store,
                plugin_host=plugin_host,
                plugin_policy=plugin_policy,
            )
            response = getattr(sync_port, "sync_record")(
                SyncRequest(record_id=record_id, payload=request_payload)
            )
        except Exception as exc:  # noqa: BLE001
            _mark_runtime_record_unsynced(
                record_store,
                record_id=record_id,
                record_revisions=record_revisions,
            )
            return RuntimeCallResult(
                status=RuntimeCallStatus.FAILED,
                value=None,
                diagnostics={"reason_code": "sync_failed", "error": str(exc)},
            )

        response_status = getattr(response, "status", "").lower()
        if response_status in {"synced", "queued", "skipped_noop"}:
            return RuntimeCallResult(
                status=RuntimeCallStatus.SUCCESS,
                value=response,
                diagnostics={"operation": "trigger_sync"},
            )
        _mark_runtime_record_unsynced(
            record_store,
            record_id=record_id,
            record_revisions=record_revisions,
        )
        return RuntimeCallResult(
            status=RuntimeCallStatus.FAILED,
            value=response,
            diagnostics={
                "reason_code": str(getattr(response, "reason_code", "sync_failed"))
            },
        )

    def emit_sync_error(event_id: str, record_id: str, reason: str) -> None:
        event_emitter(
            {
                "kind": "immediate_sync_error",
                "event_id": event_id,
                "record_id": record_id,
                "reason_code": reason,
            }
        )

    stage_handlers = {
        "resolve": lambda state: run_resolve_stage(
            state,
            fs_facts_provider=fs_facts_provider,
            processor_selector=processor_selector,
        ),
        "stabilize": lambda state: run_stabilize_stage(
            state,
            modified_event_gate=modified_event_gate,
            now_provider=now_provider,
            settle_delay_seconds=settle_delay_seconds,
        ),
        "transform": lambda state: run_transform_stage(state),
        "route": lambda state: run_route_stage(
            state,
            allowed_roots=allowed_roots,
            route_selector=route_selector,
            filename_builder=lambda state: _build_runtime_filename(
                state,
                fallback_name=(
                    filename_builder(state.candidate)
                    if state.candidate is not None
                    else "artifact.dat"
                ),
            ),
        ),
        "persist": lambda state: run_persist_stage(
            state,
            move_file=move_file,
            save_record=save_record,
            retry_planner=retry_planner,
        ),
        "post_persist": lambda state: run_post_persist_stage(
            state,
            update_bookkeeping=update_bookkeeping,
            trigger_sync=trigger_sync,
            emit_sync_error=emit_sync_error,
            immediate_sync_enabled=True,
        ),
    }

    engine = IngestionEngine[IngestionState](
        pipeline_runner=PipelineRunner(
            start_stage="resolve",
            transition_table=DEFAULT_INGESTION_TRANSITION_TABLE,
        ),
        stage_handlers=stage_handlers,
    )
    return _RuntimeIngestionEngineAdapter(
        engine,
        processing_context_builder=lambda event: _build_runtime_processing_context(
            event,
            context=context,
            clock=clock,
            plugin_policy=plugin_policy,
        ),
    )


def _resolve_route_root(settings: StartupSettings | object) -> str:
    paths = getattr(settings, "paths", None)
    candidate = getattr(paths, "dest", None)
    if isinstance(candidate, str) and candidate.strip():
        return str(PurePath(candidate))
    return "processed"


def _resolve_settle_delay_seconds(settings: StartupSettings | object) -> float:
    ingestion = getattr(settings, "ingestion", None)
    candidate = getattr(ingestion, "settle_delay_seconds", None)
    if candidate is None:
        candidate = getattr(settings, "settle_delay_seconds", 0.0)
    try:
        value = float(candidate)
    except (TypeError, ValueError):
        return 0.0
    if value < 0:
        return 0.0
    return value


def _build_runtime_filename(state: IngestionState, *, fallback_name: str) -> str:
    processor_result = state.processor_result
    if processor_result is not None:
        candidate_name = PurePath(processor_result.final_path).name
        if candidate_name.strip():
            return candidate_name
    return fallback_name


def _read_runtime_file_facts(path: str, *, clock: object) -> Mapping[str, Any]:
    path_obj = Path(path)
    fallback_modified_at = _clock_seconds(clock)
    try:
        stat_result = path_obj.stat()
        size = int(stat_result.st_size)
        modified_at = float(stat_result.st_mtime)
    except OSError:
        size = 0
        modified_at = fallback_modified_at

    return {
        "size": size,
        "modified_at": modified_at,
        "fingerprint": f"fp:{path_obj}:{size}:{int(modified_at)}",
    }


def _normalize_path(filesystem: object, value: str) -> str:
    normalize = getattr(filesystem, "normalize_path", None)
    if callable(normalize):
        try:
            return str(normalize(value))
        except Exception:  # noqa: BLE001
            return str(PurePath(value))
    return str(PurePath(value))


def _clock_seconds(clock: object) -> float:
    now_fn = getattr(clock, "now", None)
    if not callable(now_fn):
        return 0.0
    value = now_fn()
    if isinstance(value, datetime):
        return value.timestamp()
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _coerce_observed_at_datetime(
    event: Mapping[str, Any], *, clock: object
) -> datetime:
    observed_at = event.get("observed_at")
    if isinstance(observed_at, datetime):
        return observed_at
    if observed_at is not None:
        try:
            return datetime.fromtimestamp(float(observed_at), tz=UTC)
        except (TypeError, ValueError, OSError):
            pass
    now_fn = getattr(clock, "now", None)
    if callable(now_fn):
        value = now_fn()
        if isinstance(value, datetime):
            return value
    return datetime.now(UTC)


def _build_runtime_processing_context(
    event: Mapping[str, Any],
    *,
    context: StartupContext,
    clock: object,
    plugin_policy: _RuntimePluginPolicy,
) -> ProcessingContext:
    event_id = (
        str(event.get("event_id", "")).strip() or f"{context.launch.trace_id}:event"
    )
    runtime_context = RuntimeContext.from_settings(
        settings={
            "mode": context.settings.mode,
            "profile": context.settings.profile or "default",
            "session_id": f"session-{context.launch.trace_id}",
            "event_id": event_id,
            "trace_id": context.launch.trace_id,
            "selected_pc_plugin": plugin_policy.selected_pc_plugin,
            "scoped_device_plugins": plugin_policy.scoped_device_plugins,
        },
        dependency_ids={
            "clock": f"clock:{context.dependencies.selected_backends.get('observability', 'default')}",
            "ui": f"ui:{context.dependencies.selected_backends.get('ui', 'default')}",
            "sync": f"sync:{context.dependencies.selected_backends.get('sync', 'default')}",
        },
    )
    source_path = str(event.get("path", event.get("source_path", ""))).strip()
    event_type = str(
        event.get("event_type", event.get("event_kind", "created"))
    ).strip()
    candidate_event: dict[str, Any] = {
        "source_path": source_path,
        "event_type": event_type or "created",
        "observed_at": _coerce_observed_at_datetime(event, clock=clock),
        "event_id": event_id,
        "trace_id": context.launch.trace_id,
    }
    if "force_paths" in event:
        candidate_event["force_paths"] = event["force_paths"]
    elif "force_path" in event:
        candidate_event["force_paths"] = event["force_path"]
    return ProcessingContext.for_candidate(runtime_context, candidate_event)


def _extract_record_id(saved: object, *, record_payload: Mapping[str, Any]) -> str:
    if isinstance(saved, Mapping):
        candidate = saved.get("record_id")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    candidate_payload = record_payload.get("candidate")
    if isinstance(candidate_payload, Mapping):
        identity = candidate_payload.get("identity_token")
        if isinstance(identity, str) and identity.strip():
            return f"record-{identity[:12]}"
    return "record-generated"


def _extract_record_revision(saved: object, *, fallback: int) -> int:
    if isinstance(saved, Mapping):
        candidate = saved.get("revision")
        if isinstance(candidate, int):
            return candidate
        if isinstance(candidate, str) and candidate.strip():
            try:
                return int(candidate)
            except ValueError:
                return fallback
    return fallback


def _extract_runtime_record_snapshot(
    saved: object,
    *,
    record_id: str,
    revision: int,
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    if isinstance(saved, Mapping):
        snapshot_payload = saved.get("payload")
        if isinstance(snapshot_payload, Mapping):
            return {
                "record_id": str(saved.get("record_id", record_id)),
                "revision": _extract_record_revision(saved, fallback=revision),
                "payload": dict(snapshot_payload),
            }
    return {
        "record_id": record_id,
        "revision": revision,
        "payload": dict(payload),
    }


def _resolve_runtime_record_id(record_payload: Mapping[str, Any]) -> str:
    candidate_payload = record_payload.get("candidate")
    if isinstance(candidate_payload, Mapping):
        identity = candidate_payload.get("identity_token")
        if isinstance(identity, str) and identity.strip():
            return f"record-{identity[:12]}"
    target_path = record_payload.get("target_path")
    if isinstance(target_path, str) and target_path.strip():
        return f"record-{sha256(target_path.encode('utf-8')).hexdigest()[:12]}"
    return "record-generated"


def _build_runtime_sync_payload(
    state: IngestionState,
    *,
    record_store: object,
    plugin_host: object,
    plugin_policy: _RuntimePluginPolicy,
) -> Mapping[str, Any]:
    record_id = str(state.record_id or "").strip()
    payload: Mapping[str, Any] = {"record_id": record_id}
    runtime_context = getattr(state.processing_context, "runtime_context", None)
    selected_pc_plugin = plugin_policy.selected_pc_plugin
    if selected_pc_plugin is None or not isinstance(runtime_context, RuntimeContext):
        return payload

    prepare_sync_payload = getattr(plugin_host, "prepare_sync_payload", None)
    if not callable(prepare_sync_payload):
        return payload

    record_snapshot = _load_runtime_record_snapshot(
        record_store,
        record_id=record_id,
        fallback=state.record_snapshot,
    )
    return prepare_sync_payload(
        selected_pc_plugin,
        record=record_snapshot,
        context=runtime_context,
    )


def _load_runtime_record_snapshot(
    record_store: object,
    *,
    record_id: str,
    fallback: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    getter = getattr(record_store, "get", None)
    if callable(getter):
        try:
            snapshot = getter(record_id)
        except Exception:  # noqa: BLE001
            snapshot = None
        if isinstance(snapshot, Mapping):
            return dict(snapshot)
    if isinstance(fallback, Mapping):
        return dict(fallback)
    return {"record_id": record_id, "payload": {"sync_status": "pending"}}


def _mark_runtime_record_unsynced(
    record_store: object,
    *,
    record_id: str,
    record_revisions: dict[str, int],
) -> None:
    marker = getattr(record_store, "mark_unsynced", None)
    if not callable(marker):
        return
    try:
        marker(record_id)
    except Exception:  # noqa: BLE001
        return
    getter = getattr(record_store, "get", None)
    if not callable(getter):
        return
    try:
        snapshot = getter(record_id)
    except Exception:  # noqa: BLE001
        return
    if isinstance(snapshot, Mapping):
        record_revisions[record_id] = _extract_record_revision(
            snapshot,
            fallback=record_revisions.get(record_id, 0),
        )


def _select_runtime_processor(
    *,
    plugin_host: object,
    candidate: Candidate,
    scoped_plugin_ids: Sequence[str] = (),
    pc_scope_applied: bool = False,
    processor_cache: dict[str, object] | None = None,
) -> ProcessorSelection:
    if pc_scope_applied or scoped_plugin_ids:
        plugin_ids = tuple(
            str(plugin_id).strip()
            for plugin_id in scoped_plugin_ids
            if str(plugin_id).strip()
        )
    else:
        plugin_ids = _resolve_device_plugin_ids(plugin_host)

    for plugin_id in plugin_ids:
        processor, cache_hit = _build_runtime_processor(
            plugin_host=plugin_host,
            plugin_id=plugin_id,
            candidate=candidate,
            processor_cache=processor_cache,
        )
        if processor is None:
            continue
        return ProcessorSelection(
            processor=processor,
            descriptor=SelectionDescriptor(
                plugin_id=plugin_id,
                processor_key=plugin_id,
                capability_reason=(
                    (
                        "pc_scope_selected"
                        if pc_scope_applied
                        else "device_scope_selected"
                    )
                    if scoped_plugin_ids
                    else "pc_scope_default"
                ),
                cache_hit=cache_hit,
            ),
        )
    raise ProcessorNotFoundError("No runtime processor available for candidate.")


def _resolve_runtime_plugin_policy(
    *,
    application_ports: Mapping[str, object],
    context: StartupContext,
) -> _RuntimePluginPolicy:
    plugin_host = application_ports.get("plugin_host")
    if plugin_host is None:
        return _RuntimePluginPolicy(
            selected_pc_plugin=None,
            scoped_device_plugins=(),
            pc_scope_applied=False,
        )

    selected_pc_plugin = _extract_selected_pc_plugin(context.settings)
    raw_device_plugins = _extract_selected_device_plugins(context.settings)
    if selected_pc_plugin is None:
        return _RuntimePluginPolicy(
            selected_pc_plugin=None,
            scoped_device_plugins=raw_device_plugins,
            pc_scope_applied=False,
        )
    resolver = getattr(plugin_host, "resolve_device_scope_for_pc", None)
    if not callable(resolver):
        raise CompositionPluginBindingError(
            "binding for 'plugin_host' does not support PC device scope resolution"
        )

    try:
        scope = resolver(selected_pc_plugin)
    except PluginHostActivationError as exc:
        raise CompositionPluginBindingError(str(exc)) from exc

    scoped_device_plugins = tuple(scope.device_plugin_ids)
    if raw_device_plugins:
        allowed = set(raw_device_plugins)
        scoped_device_plugins = tuple(
            plugin_id for plugin_id in scoped_device_plugins if plugin_id in allowed
        )

    return _RuntimePluginPolicy(
        selected_pc_plugin=selected_pc_plugin,
        scoped_device_plugins=scoped_device_plugins,
        pc_scope_applied=True,
    )


def _extract_selected_pc_plugin(settings: object) -> str | None:
    plugins = getattr(settings, "plugins", None)
    candidate = getattr(plugins, "pc_name", None)
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip().lower()
    if isinstance(settings, Mapping):
        raw_plugins = settings.get("plugins")
        if isinstance(raw_plugins, Mapping):
            raw_candidate = raw_plugins.get("pc_name")
            if isinstance(raw_candidate, str) and raw_candidate.strip():
                return raw_candidate.strip().lower()
    return None


def _extract_selected_device_plugins(settings: object) -> tuple[str, ...]:
    plugins = getattr(settings, "plugins", None)
    candidate = getattr(plugins, "device_plugins", None)
    if isinstance(candidate, tuple | list):
        return tuple(
            str(plugin_id).strip().lower()
            for plugin_id in candidate
            if str(plugin_id).strip()
        )

    if isinstance(settings, Mapping):
        raw_plugins = settings.get("plugins")
        if isinstance(raw_plugins, Mapping):
            raw_candidate = raw_plugins.get("device_plugins", ())
            if isinstance(raw_candidate, tuple | list):
                return tuple(
                    str(plugin_id).strip().lower()
                    for plugin_id in raw_candidate
                    if str(plugin_id).strip()
                )
    return ()


def _resolve_device_plugin_ids(plugin_host: object) -> tuple[str, ...]:
    getter = getattr(plugin_host, "get_device_plugins", None)
    if not callable(getter):
        return ("default_device",)
    try:
        raw = getter()
    except Exception:  # noqa: BLE001
        return ("default_device",)
    plugin_ids = tuple(
        str(item).strip() for item in tuple(raw) if str(item).strip()  # type: ignore[arg-type]
    )
    if plugin_ids:
        return plugin_ids
    return ("default_device",)


def _build_runtime_processor(
    *,
    plugin_host: object,
    plugin_id: str,
    candidate: Candidate,
    processor_cache: dict[str, object] | None = None,
) -> tuple[object | None, bool]:
    factory = getattr(plugin_host, "create_device_processor", None)
    cache = processor_cache if isinstance(processor_cache, dict) else {}
    processor = cache.get(plugin_id)
    cache_hit = processor is not None
    if processor is None and callable(factory):
        try:
            processor = factory(plugin_id, settings={})
        except PluginHostActivationError:
            processor = None
        except Exception:  # noqa: BLE001
            processor = None
    if processor is None:
        processor = _DefaultDeviceProcessor(plugin_id)
    elif plugin_id not in cache:
        cache[plugin_id] = processor

    if not _processor_supports_runtime_candidate(processor, candidate):
        return None, cache_hit
    process = getattr(processor, "process", None)
    if not callable(process):
        return None, cache_hit
    return processor, cache_hit


def _processor_supports_runtime_candidate(
    processor: object,
    candidate: Candidate,
) -> bool:
    settings = getattr(processor, "settings", None)
    source_extensions = getattr(settings, "source_extensions", None)
    candidate_extension = Path(candidate.source_path).suffix.lower()
    if isinstance(source_extensions, tuple | list):
        normalized_extensions = {
            str(token).strip().lower()
            for token in source_extensions
            if str(token).strip()
        }
        if candidate_extension:
            return candidate_extension in normalized_extensions

    can_process = getattr(processor, "can_process", None)
    if callable(can_process):
        try:
            return bool(can_process({"source_path": candidate.source_path}))
        except Exception:  # noqa: BLE001
            return False
    return True


class _ClockPort:
    def now(self) -> datetime:  # pragma: no cover - protocol-like marker
        raise NotImplementedError


def _is_clock_port(value: object) -> bool:
    return callable(getattr(value, "now", None))


class _SystemClock(_ClockPort):
    def now(self) -> datetime:
        return datetime.now(UTC)


class _RuntimeIngestionEngineAdapter:
    def __init__(
        self,
        engine: IngestionEngine[IngestionState],
        *,
        processing_context_builder: Callable[[Mapping[str, Any]], ProcessingContext],
    ) -> None:
        self._engine = engine
        self._processing_context_builder = processing_context_builder

    def process(
        self,
        *,
        event: Mapping[str, Any],
        processing_context: Any | None = None,
    ) -> IngestionOutcome[object]:
        resolved_processing_context = processing_context
        if not isinstance(resolved_processing_context, ProcessingContext):
            resolved_processing_context = self._processing_context_builder(event)
        return self._engine.process(
            event=event,
            initial_state_factory=lambda payload: IngestionState.from_event(
                payload,
                processing_context=resolved_processing_context,
            ),
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
        return ("default_device",)

    def get_pc_plugins(self) -> tuple[object, ...]:
        return ()

    def get_by_capability(self, capability: str) -> tuple[object, ...]:
        return ()


class _ModifiedEventGateState:
    def __init__(self) -> None:
        self._last_seen: dict[str, float] = {}

    def evaluate(self, event_key: str, event_timestamp: float) -> object:
        last_seen = self._last_seen.get(event_key)
        self._last_seen[event_key] = event_timestamp
        decision = "allow"
        reason_code = "outside_debounce_window"
        if last_seen is not None and event_timestamp <= last_seen:
            decision = "drop_duplicate"
            reason_code = "inside_debounce_window"
        return MappingProxyType({"decision": decision, "reason_code": reason_code})


class _DefaultDeviceProcessor:
    def __init__(self, plugin_id: str) -> None:
        self.plugin_id = plugin_id

    def can_process(self, candidate: Mapping[str, Any]) -> bool:
        source_path = str(candidate.get("source_path", "")).strip()
        return bool(source_path)

    def process(self, candidate: Mapping[str, Any], context: object) -> object:
        _ = context
        return {
            "final_path": str(candidate.get("source_path", "")),
            "datatype": f"{self.plugin_id}/output",
        }


class _FilesystemAdapter:
    def normalize_path(self, value: str) -> str:
        return str(PurePath(value))
