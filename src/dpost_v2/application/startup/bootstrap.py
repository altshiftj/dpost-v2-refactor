"""Startup bootstrap orchestration for V2 runtime assembly."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Callable, Mapping

from dpost_v2.application.startup.context import (
    LaunchMetadata,
    StartupContext,
    build_startup_context,
)
from dpost_v2.application.startup.settings import StartupSettings
from dpost_v2.application.startup.settings_service import (
    SettingsCache,
    SettingsLoadFailure,
    SettingsLoadResult,
    load_startup_settings,
)
from dpost_v2.runtime.composition import CompositionBundle
from dpost_v2.runtime.composition import compose_runtime as compose_runtime_root
from dpost_v2.runtime.startup_dependencies import StartupDependencies
from dpost_v2.runtime.startup_dependencies import (
    resolve_startup_dependencies as resolve_startup_dependencies_root,
)

_STARTUP_DIAGNOSTIC_FIELDS: tuple[str, ...] = (
    "requested_mode",
    "requested_profile",
    "mode",
    "profile",
    "boot_timestamp_utc",
    "settings_fingerprint",
    "settings_provenance",
    "selected_backends",
    "plugin_backend",
    "plugin_visibility",
)


@dataclass(frozen=True)
class BootstrapRequest:
    """Input contract from entrypoint to bootstrap orchestration."""

    mode: str
    profile: str | None
    trace_id: str
    metadata: Mapping[str, Any] = MappingProxyType({})


@dataclass(frozen=True)
class StartupFailure:
    """Normalized startup failure payload."""

    stage: str
    error_type: str
    message: str


@dataclass(frozen=True)
class StartupEvent:
    """Deterministic startup event emitted by bootstrap."""

    name: str
    trace_id: str
    payload: Mapping[str, Any] = MappingProxyType({})


@dataclass(frozen=True)
class BootstrapResult:
    """Bootstrap success/failure envelope."""

    is_success: bool
    context: StartupContext | None = None
    runtime_handle: Any = None
    failure: StartupFailure | None = None


def run(
    *,
    request: BootstrapRequest,
    emit_event: Callable[[StartupEvent], None],
    launch_runtime: Callable[[Any, StartupContext], Any] | None = None,
    settings_cache: SettingsCache | None = None,
    root_hint: str | os.PathLike[str] | None = None,
    environment: Mapping[str, str] | None = None,
) -> BootstrapResult:
    """Run bootstrap using default V2 settings/dependency/composition services."""
    runtime_launcher = launch_runtime or (lambda app, _context: app)

    def _load_settings(received_request: BootstrapRequest) -> SettingsLoadResult:
        return load_startup_settings(
            received_request,
            root_hint=root_hint,
            cache=settings_cache,
        )

    def _resolve_dependencies(
        settings: StartupSettings,
        _request: BootstrapRequest,
    ) -> StartupDependencies:
        resolved_environment = (
            dict(os.environ) if environment is None else dict(environment)
        )
        return resolve_startup_dependencies_root(
            settings=settings.to_dependency_payload(),
            environment=resolved_environment,
        )

    return run_bootstrap(
        request=request,
        load_settings=_load_settings,
        resolve_dependencies=_resolve_dependencies,
        compose_runtime=compose_runtime_root,
        launch_runtime=runtime_launcher,
        emit_event=emit_event,
    )


def run_bootstrap(
    *,
    request: BootstrapRequest,
    load_settings: Callable[[BootstrapRequest], Any],
    resolve_dependencies: Callable[[Any, BootstrapRequest], StartupDependencies],
    compose_runtime: Callable[[StartupContext], CompositionBundle],
    launch_runtime: Callable[[Any, StartupContext], Any],
    emit_event: Callable[[StartupEvent], None],
    now_utc: Callable[[], datetime] | None = None,
) -> BootstrapResult:
    """Run fixed startup sequence: settings -> dependencies -> context -> composition -> launch."""
    timestamp_factory = now_utc or (lambda: datetime.now(UTC))
    boot_timestamp = timestamp_factory().isoformat()
    event_diagnostics = _initialize_event_diagnostics(
        request=request,
        boot_timestamp_utc=boot_timestamp,
    )
    cleanup_hooks: list[Callable[[], None]] = []

    _emit_started(request, emit_event, event_diagnostics=event_diagnostics)

    try:
        loaded_settings = load_settings(request)
        settings, settings_provenance, settings_fingerprint = _unwrap_settings(
            loaded_settings
        )
        _update_diagnostics_with_settings(
            event_diagnostics,
            settings=settings,
            settings_provenance=settings_provenance,
            settings_fingerprint=settings_fingerprint,
        )
    except (
        Exception
    ) as exc:  # pragma: no cover - exercised by tests through result path
        return _build_failure_result(
            stage="settings",
            exc=exc,
            request=request,
            event_diagnostics=event_diagnostics,
            cleanup_hooks=cleanup_hooks,
            emit_event=emit_event,
        )

    try:
        dependencies = resolve_dependencies(settings, request)
        if dependencies.cleanup is not None:
            cleanup_hooks.append(dependencies.cleanup)
    except Exception as exc:
        return _build_failure_result(
            stage="dependencies",
            exc=exc,
            request=request,
            event_diagnostics=event_diagnostics,
            cleanup_hooks=cleanup_hooks,
            emit_event=emit_event,
        )
    _update_diagnostics_with_dependencies(event_diagnostics, dependencies=dependencies)

    try:
        context = build_startup_context(
            settings=settings,
            dependencies=dependencies,
            launch_meta=LaunchMetadata(
                requested_mode=request.mode,
                requested_profile=request.profile,
                trace_id=request.trace_id,
                process_id=os.getpid(),
                boot_timestamp_utc=boot_timestamp,
            ),
        )
    except Exception as exc:
        return _build_failure_result(
            stage="context",
            exc=exc,
            request=request,
            event_diagnostics=event_diagnostics,
            cleanup_hooks=cleanup_hooks,
            emit_event=emit_event,
        )

    try:
        composition = compose_runtime(context)
        cleanup_hooks.append(composition.shutdown_all)
    except Exception as exc:
        return _build_failure_result(
            stage="composition",
            exc=exc,
            request=request,
            event_diagnostics=event_diagnostics,
            cleanup_hooks=cleanup_hooks,
            emit_event=emit_event,
        )
    _update_diagnostics_with_composition(event_diagnostics, composition=composition)

    try:
        runtime_handle = launch_runtime(composition.app, context)
    except Exception as exc:
        return _build_failure_result(
            stage="launch",
            exc=exc,
            request=request,
            event_diagnostics=event_diagnostics,
            cleanup_hooks=cleanup_hooks,
            emit_event=emit_event,
        )

    emit_event(
        StartupEvent(
            name="startup_succeeded",
            trace_id=request.trace_id,
            payload=_build_startup_event_payload(event_diagnostics),
        )
    )
    return BootstrapResult(
        is_success=True,
        context=context,
        runtime_handle=runtime_handle,
        failure=None,
    )


def _emit_started(
    request: BootstrapRequest,
    emit_event: Callable[[StartupEvent], None],
    *,
    event_diagnostics: Mapping[str, Any],
) -> None:
    metadata = dict(request.metadata)
    emit_event(
        StartupEvent(
            name="startup_started",
            trace_id=request.trace_id,
            payload=_build_startup_event_payload(
                event_diagnostics,
                extra_payload={"metadata": metadata},
            ),
        )
    )


def _build_failure_result(
    *,
    stage: str,
    exc: Exception,
    request: BootstrapRequest,
    event_diagnostics: Mapping[str, Any],
    cleanup_hooks: list[Callable[[], None]],
    emit_event: Callable[[StartupEvent], None],
) -> BootstrapResult:
    _run_cleanup(cleanup_hooks)
    failure = StartupFailure(
        stage=stage,
        error_type=type(exc).__name__,
        message=str(exc),
    )
    emit_event(
        StartupEvent(
            name="startup_failed",
            trace_id=request.trace_id,
            payload=_build_startup_event_payload(
                event_diagnostics,
                extra_payload={
                    "stage": failure.stage,
                    "error_type": failure.error_type,
                    "message": failure.message,
                },
            ),
        )
    )
    return BootstrapResult(is_success=False, failure=failure)


def _run_cleanup(cleanup_hooks: list[Callable[[], None]]) -> None:
    for hook in reversed(cleanup_hooks):
        try:
            hook()
        except Exception:
            continue


def _unwrap_settings(loaded: Any) -> StartupSettings | Any:
    if not isinstance(loaded, SettingsLoadResult):
        return loaded, MappingProxyType({}), None

    if loaded.is_success and loaded.settings is not None:
        return loaded.settings, loaded.provenance, loaded.fingerprint

    failure = loaded.failure or SettingsLoadFailure(
        stage="settings_service",
        error_type="SettingsLoadFailure",
        message="Settings load returned unsuccessful result.",
    )
    raise RuntimeError(f"{failure.error_type}: {failure.message}")


def _initialize_event_diagnostics(
    *,
    request: BootstrapRequest,
    boot_timestamp_utc: str,
) -> dict[str, Any]:
    return {
        "requested_mode": request.mode,
        "requested_profile": request.profile,
        "mode": request.mode,
        "profile": request.profile,
        "boot_timestamp_utc": boot_timestamp_utc,
        "settings_fingerprint": None,
        "settings_provenance": {},
        "selected_backends": {},
        "plugin_backend": None,
        "plugin_visibility": "unknown",
    }


def _update_diagnostics_with_settings(
    diagnostics: dict[str, Any],
    *,
    settings: StartupSettings | Any,
    settings_provenance: Mapping[str, str],
    settings_fingerprint: str | None,
) -> None:
    diagnostics["settings_fingerprint"] = settings_fingerprint
    diagnostics["settings_provenance"] = dict(settings_provenance)
    if hasattr(settings, "mode"):
        diagnostics["mode"] = getattr(settings, "mode")
    if hasattr(settings, "profile"):
        diagnostics["profile"] = getattr(settings, "profile")

    plugin_backend = _resolve_plugin_backend_from_settings(settings)
    if plugin_backend is not None:
        diagnostics["plugin_backend"] = plugin_backend
        diagnostics["plugin_visibility"] = "configured"


def _resolve_plugin_backend_from_settings(settings: object) -> str | None:
    if isinstance(settings, Mapping):
        backends = settings.get("backends")
        if isinstance(backends, Mapping):
            candidate = backends.get("plugins")
            if candidate is not None:
                token = str(candidate).strip().lower()
                if token:
                    return token

    payload_builder = getattr(settings, "to_dependency_payload", None)
    if not callable(payload_builder):
        return None

    payload = payload_builder()
    if not isinstance(payload, Mapping):
        return None
    backends = payload.get("backends")
    if not isinstance(backends, Mapping):
        return None
    candidate = backends.get("plugins")
    if candidate is None:
        return None
    token = str(candidate).strip().lower()
    return token or None


def _update_diagnostics_with_dependencies(
    diagnostics: dict[str, Any],
    *,
    dependencies: StartupDependencies,
) -> None:
    selected_backends = dict(dependencies.selected_backends)
    diagnostics["selected_backends"] = selected_backends
    plugin_backend = selected_backends.get("plugins")
    if plugin_backend is None:
        return
    diagnostics["plugin_backend"] = str(plugin_backend)
    diagnostics["plugin_visibility"] = "configured"


def _update_diagnostics_with_composition(
    diagnostics: dict[str, Any],
    *,
    composition: CompositionBundle,
) -> None:
    selected_backends = composition.diagnostics.get("selected_backends")
    if isinstance(selected_backends, Mapping):
        diagnostics["selected_backends"] = dict(selected_backends)

    plugin_backend = composition.diagnostics.get("plugin_backend")
    if plugin_backend is not None:
        token = str(plugin_backend).strip()
        if token:
            diagnostics["plugin_backend"] = token

    plugin_visibility = composition.diagnostics.get("plugin_visibility")
    if isinstance(plugin_visibility, str) and plugin_visibility.strip():
        diagnostics["plugin_visibility"] = plugin_visibility.strip().lower()
        return
    if "plugins" in composition.port_bindings:
        diagnostics["plugin_visibility"] = "bound"


def _build_startup_event_payload(
    diagnostics: Mapping[str, Any],
    *,
    extra_payload: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    payload = {
        key: _copy_value(diagnostics.get(key)) for key in _STARTUP_DIAGNOSTIC_FIELDS
    }
    for key, value in dict(extra_payload or {}).items():
        payload[key] = _copy_value(value)
    return MappingProxyType(payload)


def _copy_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _copy_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_copy_value(item) for item in value)
    if isinstance(value, list):
        return [_copy_value(item) for item in value]
    return value
