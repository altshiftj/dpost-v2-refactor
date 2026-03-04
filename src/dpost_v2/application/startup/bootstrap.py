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
    cleanup_hooks: list[Callable[[], None]] = []

    _emit_started(request, emit_event)

    try:
        loaded_settings = load_settings(request)
        settings = _unwrap_settings(loaded_settings)
    except Exception as exc:  # pragma: no cover - exercised by tests through result path
        return _build_failure_result(
            stage="settings",
            exc=exc,
            request=request,
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
            cleanup_hooks=cleanup_hooks,
            emit_event=emit_event,
        )

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
            cleanup_hooks=cleanup_hooks,
            emit_event=emit_event,
        )

    try:
        runtime_handle = launch_runtime(composition.app, context)
    except Exception as exc:
        return _build_failure_result(
            stage="launch",
            exc=exc,
            request=request,
            cleanup_hooks=cleanup_hooks,
            emit_event=emit_event,
        )

    emit_event(
        StartupEvent(
            name="startup_succeeded",
            trace_id=request.trace_id,
            payload=MappingProxyType(
                {
                    "mode": request.mode,
                    "profile": request.profile,
                    "boot_timestamp_utc": boot_timestamp,
                }
            ),
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
) -> None:
    metadata = dict(request.metadata)
    emit_event(
        StartupEvent(
            name="startup_started",
            trace_id=request.trace_id,
            payload=MappingProxyType(
                {
                    "mode": request.mode,
                    "profile": request.profile,
                    "metadata": metadata,
                }
            ),
        )
    )


def _build_failure_result(
    *,
    stage: str,
    exc: Exception,
    request: BootstrapRequest,
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
            payload=MappingProxyType(
                {
                    "stage": failure.stage,
                    "error_type": failure.error_type,
                    "message": failure.message,
                }
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
        return loaded

    if loaded.is_success and loaded.settings is not None:
        return loaded.settings

    failure = loaded.failure or SettingsLoadFailure(
        stage="settings_service",
        error_type="SettingsLoadFailure",
        message="Settings load returned unsuccessful result.",
    )
    raise RuntimeError(f"{failure.error_type}: {failure.message}")
