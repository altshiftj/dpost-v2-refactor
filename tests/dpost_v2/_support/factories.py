"""Deterministic object factories for V2 test harnesses."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from dpost_v2.application.contracts.context import RuntimeContext
from dpost_v2.application.startup.bootstrap import BootstrapRequest
from dpost_v2.application.startup.context import LaunchMetadata, StartupContext
from dpost_v2.application.startup.context import (
    build_startup_context as build_startup_context_contract,
)
from dpost_v2.application.startup.settings import StartupSettings, from_raw
from dpost_v2.runtime.startup_dependencies import StartupDependencies
from tests.dpost_v2._support.runtime_doubles import build_recording_factories

DEFAULT_TRACE_ID = "trace-0001"
DEFAULT_EVENT_ID = "event-0001"
DEFAULT_SESSION_ID = "session-0001"
DEFAULT_BOOT_TIMESTAMP = datetime(2026, 3, 4, 12, 0, 0, tzinfo=UTC)
DEFAULT_PROCESS_ID = 4242


def build_bootstrap_request(
    *,
    mode: str = "headless",
    profile: str | None = "ci",
    trace_id: str = DEFAULT_TRACE_ID,
    metadata: Mapping[str, Any] | None = None,
) -> BootstrapRequest:
    """Build a deterministic bootstrap request for startup tests."""
    return BootstrapRequest(
        mode=mode,
        profile=profile,
        trace_id=trace_id,
        metadata=dict(metadata or {}),
    )


def build_startup_settings(
    *,
    root_hint: Path | str,
    mode: str = "headless",
    profile: str | None = "ci",
    ui_backend: str = "headless",
    sync_backend: str = "noop",
    retry_limit: int = 1,
    retry_delay_seconds: float = 0.25,
    prefix: str = "LAB",
    naming_policy: str = "prefix_only",
    source_fingerprint: str | None = "harness-fixture",
) -> StartupSettings:
    """Build immutable startup settings from deterministic defaults."""
    raw_payload = {
        "mode": mode,
        "profile": profile,
        "paths": {
            "root": "runtime",
            "watch": "incoming",
            "dest": "processed",
            "staging": "tmp",
        },
        "ui": {"backend": ui_backend},
        "sync": {"backend": sync_backend, "api_token": "token"},
        "ingestion": {
            "retry_limit": retry_limit,
            "retry_delay_seconds": retry_delay_seconds,
        },
        "naming": {"prefix": prefix, "policy": naming_policy},
    }
    return from_raw(
        raw_payload,
        root_hint=Path(root_hint),
        source_fingerprint=source_fingerprint,
    )


def build_startup_dependencies(
    *,
    ui_backend: str = "headless",
    sync_backend: str = "noop",
    call_log: list[str] | None = None,
    cleanup=None,
) -> StartupDependencies:
    """Build deterministic startup dependencies with all composition ports."""
    init_calls = call_log if call_log is not None else []
    factory_ports = (
        "observability",
        "storage",
        "sync",
        "ui",
        "event_sink",
        "plugins",
        "clock",
        "filesystem",
    )
    factories = build_recording_factories(
        factory_ports,
        call_log=init_calls,
        adapter_builder=lambda port: _default_dependency_adapter(
            port=port,
            ui_backend=ui_backend,
            sync_backend=sync_backend,
        ),
    )
    return StartupDependencies(
        factories=factories,
        selected_backends={
            "ui": ui_backend,
            "sync": sync_backend,
            "plugins": "builtin",
            "observability": "structured",
            "storage": "filesystem",
        },
        lazy_factories=frozenset({"sync", "plugins"}),
        warnings=(),
        diagnostics={"init_call_log": init_calls},
        cleanup=cleanup,
    )


def _default_dependency_adapter(
    *,
    port: str,
    ui_backend: str,
    sync_backend: str,
) -> dict[str, object]:
    if port == "ui":
        return {"kind": "ui", "backend": ui_backend}
    if port == "sync":
        return {"kind": "sync", "backend": sync_backend}
    if port == "storage":
        return {"kind": "storage", "backend": "filesystem"}
    if port == "observability":
        return {"kind": "observability", "backend": "structured"}
    if port == "plugins":
        return {"kind": "plugins", "backend": "builtin"}
    if port == "event_sink":
        return {"kind": "event_sink"}
    if port == "clock":
        return {"kind": "clock"}
    if port == "filesystem":
        return {"kind": "filesystem"}
    return {"kind": port}


def build_startup_context(
    *,
    root_hint: Path | str,
    settings: StartupSettings | None = None,
    dependencies: StartupDependencies | None = None,
    mode: str = "headless",
    profile: str | None = "ci",
    trace_id: str = DEFAULT_TRACE_ID,
    process_id: int = DEFAULT_PROCESS_ID,
    boot_timestamp: datetime = DEFAULT_BOOT_TIMESTAMP,
) -> StartupContext:
    """Build startup context with deterministic launch metadata defaults."""
    resolved_settings = settings or build_startup_settings(
        root_hint=Path(root_hint),
        mode=mode,
        profile=profile,
        ui_backend="desktop" if mode == "desktop" else "headless",
    )
    resolved_dependencies = dependencies or build_startup_dependencies(
        ui_backend="desktop" if resolved_settings.mode == "desktop" else "headless",
    )
    launch = LaunchMetadata(
        requested_mode=resolved_settings.mode,
        requested_profile=resolved_settings.profile,
        trace_id=trace_id,
        process_id=process_id,
        boot_timestamp_utc=boot_timestamp.isoformat(),
    )
    return build_startup_context_contract(
        settings=resolved_settings,
        dependencies=resolved_dependencies,
        launch_meta=launch,
    )


def build_runtime_context(
    *,
    mode: str = "headless",
    profile: str = "ci",
    session_id: str = DEFAULT_SESSION_ID,
    event_id: str = DEFAULT_EVENT_ID,
    trace_id: str = DEFAULT_TRACE_ID,
    dependency_ids: Mapping[str, str] | None = None,
    settings_overrides: Mapping[str, object] | None = None,
) -> RuntimeContext:
    """Build runtime context with stable dependency ids and tokens."""
    settings_payload: dict[str, object] = {
        "mode": mode,
        "profile": profile,
        "session_id": session_id,
        "event_id": event_id,
        "trace_id": trace_id,
    }
    if settings_overrides:
        settings_payload.update(dict(settings_overrides))
    resolved_dependency_ids = dict(
        dependency_ids
        or {
            "clock": "clock:default",
            "sync": "sync:default",
            "ui": "ui:default",
        }
    )
    return RuntimeContext.from_settings(
        settings=settings_payload,
        dependency_ids=resolved_dependency_ids,
    )
