"""Runtime composition root for V2 startup context wiring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path, PurePath
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Sequence

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
from dpost_v2.application.ingestion.state import IngestionState
from dpost_v2.application.runtime.dpost_app import DPostApp
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
class CompositionBundle:
    """Fully wired runtime application bundle."""

    app: Any
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
        },
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
) -> Iterable[Mapping[str, Any]]:
    candidate = getattr(ui_port, "iter_events", None)
    if callable(candidate):
        source = candidate()
        if isinstance(source, Iterable):
            return source
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
                key=lambda path: str(path),
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


def _build_runtime_ingestion_engine(
    *,
    application_ports: Mapping[str, object],
    context: StartupContext,
    event_emitter: Callable[[Mapping[str, Any]], None],
) -> object:
    plugin_host = application_ports["plugin_host"]
    file_ops = application_ports["file_ops"]
    record_store = application_ports["record_store"]
    sync_port = application_ports["sync"]
    filesystem = application_ports["filesystem"]
    clock = application_ports["clock"]

    gate_state = _ModifiedEventGateState()
    record_revisions: dict[str, int] = {}
    settle_delay_seconds = _resolve_settle_delay_seconds(context.settings)
    route_root = _resolve_route_root(context.settings)
    allowed_roots = (route_root,)

    def fs_facts_provider(path: str) -> Mapping[str, Any]:
        normalized_path = _normalize_path(filesystem, path)
        now_seconds = _clock_seconds(clock)
        return {
            "size": 0,
            "modified_at": now_seconds,
            "fingerprint": f"fp:{normalized_path}:{int(now_seconds)}",
        }

    def processor_selector(candidate: Candidate) -> ProcessorSelection:
        selection = _select_runtime_processor(
            plugin_host=plugin_host,
            candidate=candidate,
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
            saved = getattr(record_store, "save")(
                {
                    "record_id": record_id,
                    "revision": next_revision,
                    "payload": {
                        "candidate": dict(record_payload.get("candidate", {})),
                        "target_path": record_payload.get("target_path"),
                        "sync_status": "pending",
                    },
                }
            )
            record_id = _extract_record_id(saved, record_payload=record_payload)
            record_revisions[record_id] = _extract_record_revision(
                saved,
                fallback=next_revision,
            )
            return RuntimeCallResult(
                status=RuntimeCallStatus.SUCCESS,
                value={
                    "record_id": record_id,
                    "revision": record_revisions[record_id],
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
                            "persisted_path": getattr(candidate, "persisted_path", None),
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

    def trigger_sync(record_id: str) -> RuntimeCallResult:
        try:
            response = getattr(sync_port, "sync_record")(
                SyncRequest(record_id=record_id, payload={"record_id": record_id})
            )
        except Exception as exc:  # noqa: BLE001
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
        "route": lambda state: run_route_stage(
            state,
            allowed_roots=allowed_roots,
            route_selector=route_selector,
            filename_builder=filename_builder,
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
    return _RuntimeIngestionEngineAdapter(engine)


def _resolve_route_root(settings: StartupSettings | object) -> str:
    paths = getattr(settings, "paths", None)
    candidate = getattr(paths, "dest", None)
    if isinstance(candidate, str) and candidate.strip():
        return str(PurePath(candidate))
    return "processed"


def _resolve_settle_delay_seconds(settings: StartupSettings | object) -> float:
    ingestion = getattr(settings, "ingestion", None)
    candidate = getattr(ingestion, "retry_delay_seconds", 0.0)
    try:
        value = float(candidate)
    except (TypeError, ValueError):
        return 0.0
    if value < 0:
        return 0.0
    return value


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


def _select_runtime_processor(
    *,
    plugin_host: object,
    candidate: Candidate,
) -> ProcessorSelection:
    plugin_ids = _resolve_device_plugin_ids(plugin_host)
    for plugin_id in plugin_ids:
        processor = _build_runtime_processor(
            plugin_host=plugin_host,
            plugin_id=plugin_id,
            candidate=candidate,
        )
        if processor is None:
            continue
        return ProcessorSelection(
            processor=processor,
            descriptor=SelectionDescriptor(
                plugin_id=plugin_id,
                processor_key=plugin_id,
                capability_reason="pc_scope_default",
                cache_hit=False,
            ),
        )
    raise ProcessorNotFoundError("No runtime processor available for candidate.")


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
) -> object | None:
    factory = getattr(plugin_host, "create_device_processor", None)
    processor = None
    if callable(factory):
        try:
            processor = factory(plugin_id, settings={})
        except PluginHostActivationError:
            processor = None
        except Exception:  # noqa: BLE001
            processor = None
    if processor is None:
        processor = _DefaultDeviceProcessor(plugin_id)

    can_process = getattr(processor, "can_process", None)
    if callable(can_process):
        try:
            supported = bool(can_process({"source_path": candidate.source_path}))
        except Exception:  # noqa: BLE001
            supported = False
        if not supported:
            return None
    process = getattr(processor, "process", None)
    if not callable(process):
        return None
    return processor


class _ClockPort:
    def now(self) -> datetime:  # pragma: no cover - protocol-like marker
        raise NotImplementedError


def _is_clock_port(value: object) -> bool:
    return callable(getattr(value, "now", None))


class _SystemClock(_ClockPort):
    def now(self) -> datetime:
        return datetime.now(UTC)


class _RuntimeIngestionEngineAdapter:
    def __init__(self, engine: IngestionEngine[IngestionState]) -> None:
        self._engine = engine

    def process(
        self,
        *,
        event: Mapping[str, Any],
        processing_context: Any | None = None,
    ) -> IngestionOutcome[object]:
        _ = processing_context
        return self._engine.process(
            event=event,
            initial_state_factory=IngestionState.from_event,
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
            "plugin_id": self.plugin_id,
        }


class _FilesystemAdapter:
    def normalize_path(self, value: str) -> str:
        return str(PurePath(value))
