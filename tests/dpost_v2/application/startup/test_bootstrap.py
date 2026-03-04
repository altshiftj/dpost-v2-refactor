from __future__ import annotations

from dataclasses import dataclass

import pytest

from dpost_v2.application.startup.bootstrap import BootstrapRequest, run_bootstrap
from dpost_v2.application.startup.settings_service import (
    SettingsLoadFailure,
    SettingsLoadResult,
    load_startup_settings,
)
from dpost_v2.runtime.composition import CompositionBundle
from dpost_v2.runtime.composition import compose_runtime
from dpost_v2.runtime.startup_dependencies import StartupDependencies
from dpost_v2.runtime.startup_dependencies import resolve_startup_dependencies


@dataclass(frozen=True)
class FakeSettings:
    mode: str = "headless"
    profile: str = "ci"


class DummyApp:
    pass


def _dependencies(*, cleanup=None) -> StartupDependencies:
    return StartupDependencies(
        factories={
            "ui": lambda: object(),
            "event_sink": lambda: object(),
        },
        selected_backends={"ui": "headless", "sync": "noop", "plugins": "builtin"},
        lazy_factories=frozenset(),
        warnings=(),
        cleanup=cleanup,
    )


def test_bootstrap_orchestrates_startup_in_fixed_order() -> None:
    request = BootstrapRequest(mode="headless", profile="ci", trace_id="trace-001")
    stage_calls: list[str] = []
    events = []
    settings = FakeSettings()
    dependencies = _dependencies()

    def load_settings(received_request):
        stage_calls.append("settings")
        assert received_request is request
        return settings

    def resolve_dependencies(resolved_settings, received_request):
        stage_calls.append("dependencies")
        assert resolved_settings is settings
        assert received_request is request
        return dependencies

    def compose(context):
        stage_calls.append("composition")
        assert context.settings is settings
        assert context.dependencies is dependencies
        return CompositionBundle(
            app=DummyApp(),
            port_bindings={"ui": object(), "event_sink": object()},
            diagnostics={"ui_backend": "headless"},
            shutdown_all=lambda: stage_calls.append("composition_shutdown"),
        )

    def launch_runtime(app, context):
        stage_calls.append("launch")
        assert isinstance(app, DummyApp)
        assert context.settings is settings
        return "runtime-handle"

    result = run_bootstrap(
        request=request,
        load_settings=load_settings,
        resolve_dependencies=resolve_dependencies,
        compose_runtime=compose,
        launch_runtime=launch_runtime,
        emit_event=events.append,
    )

    assert stage_calls == ["settings", "dependencies", "composition", "launch"]
    assert [event.name for event in events] == ["startup_started", "startup_succeeded"]
    assert result.is_success is True
    assert result.runtime_handle == "runtime-handle"
    assert result.failure is None


def test_bootstrap_short_circuits_when_settings_fail() -> None:
    request = BootstrapRequest(mode="headless", profile="ci", trace_id="trace-002")
    stage_calls: list[str] = []
    events = []

    def load_settings(_request):
        stage_calls.append("settings")
        raise RuntimeError("invalid settings")

    def resolve_dependencies(_settings, _request):
        pytest.fail("dependency resolution must not run after settings failure")

    def compose(_context):
        pytest.fail("composition must not run after settings failure")

    def launch_runtime(_app, _context):
        pytest.fail("launch must not run after settings failure")

    result = run_bootstrap(
        request=request,
        load_settings=load_settings,
        resolve_dependencies=resolve_dependencies,
        compose_runtime=compose,
        launch_runtime=launch_runtime,
        emit_event=events.append,
    )

    assert stage_calls == ["settings"]
    assert [event.name for event in events] == ["startup_started", "startup_failed"]
    assert result.is_success is False
    assert result.failure is not None
    assert result.failure.stage == "settings"


def test_bootstrap_runs_cleanup_when_composition_fails() -> None:
    request = BootstrapRequest(mode="headless", profile="ci", trace_id="trace-003")
    stage_calls: list[str] = []
    events = []
    settings = FakeSettings()

    def load_settings(_request):
        stage_calls.append("settings")
        return settings

    def resolve_dependencies(_settings, _request):
        stage_calls.append("dependencies")
        return _dependencies(cleanup=lambda: stage_calls.append("deps_cleanup"))

    def compose(_context):
        stage_calls.append("composition")
        raise RuntimeError("composition failed")

    result = run_bootstrap(
        request=request,
        load_settings=load_settings,
        resolve_dependencies=resolve_dependencies,
        compose_runtime=compose,
        launch_runtime=lambda _app, _context: "unused",
        emit_event=events.append,
    )

    assert stage_calls == ["settings", "dependencies", "composition", "deps_cleanup"]
    assert [event.name for event in events] == ["startup_started", "startup_failed"]
    assert result.is_success is False
    assert result.failure is not None
    assert result.failure.stage == "composition"


def test_bootstrap_cleans_up_composition_then_dependencies_on_launch_failure() -> None:
    request = BootstrapRequest(mode="headless", profile="ci", trace_id="trace-004")
    cleanup_calls: list[str] = []
    settings = FakeSettings()

    def load_settings(_request):
        return settings

    def resolve_dependencies(_settings, _request):
        return _dependencies(cleanup=lambda: cleanup_calls.append("deps_cleanup"))

    def compose(_context):
        return CompositionBundle(
            app=DummyApp(),
            port_bindings={"ui": object(), "event_sink": object()},
            diagnostics={},
            shutdown_all=lambda: cleanup_calls.append("composition_shutdown"),
        )

    def launch_runtime(_app, _context):
        raise RuntimeError("launch failed")

    result = run_bootstrap(
        request=request,
        load_settings=load_settings,
        resolve_dependencies=resolve_dependencies,
        compose_runtime=compose,
        launch_runtime=launch_runtime,
        emit_event=lambda _event: None,
    )

    assert result.is_success is False
    assert result.failure is not None
    assert result.failure.stage == "launch"
    assert cleanup_calls == ["composition_shutdown", "deps_cleanup"]


def test_bootstrap_short_circuits_on_typed_settings_result_failure() -> None:
    request = BootstrapRequest(mode="headless", profile="ci", trace_id="trace-005")
    events = []

    def load_settings(_request):
        return SettingsLoadResult(
            is_success=False,
            failure=SettingsLoadFailure(
                stage="validation",
                error_type="SettingsValidationError",
                message="invalid config",
            ),
        )

    result = run_bootstrap(
        request=request,
        load_settings=load_settings,
        resolve_dependencies=lambda _settings, _request: pytest.fail(
            "dependency resolution must not run after typed settings failure"
        ),
        compose_runtime=lambda _context: pytest.fail(
            "composition must not run after typed settings failure"
        ),
        launch_runtime=lambda _app, _context: pytest.fail(
            "launch must not run after typed settings failure"
        ),
        emit_event=events.append,
    )

    assert result.is_success is False
    assert result.failure is not None
    assert result.failure.stage == "settings"
    assert [event.name for event in events] == ["startup_started", "startup_failed"]


def test_bootstrap_integration_with_settings_service_and_runtime_modules(tmp_path) -> None:
    request = BootstrapRequest(mode="headless", profile="ci", trace_id="trace-006")
    events = []
    seen_context = []

    def load_settings(received_request):
        return load_startup_settings(
            received_request,
            root_hint=tmp_path,
            sources={
                "defaults": {
                    "mode": "headless",
                    "profile": "default",
                    "paths": {"root": "runtime"},
                    "ui": {"backend": "headless"},
                    "sync": {"backend": "noop"},
                    "ingestion": {"retry_limit": 1, "retry_delay_seconds": 1.0},
                    "naming": {"prefix": "DEF", "policy": "prefix_only"},
                },
                "file": {},
                "environment": {},
                "cli": {"profile": "ci"},
            },
        )

    def resolve_dependencies(settings, _request):
        return resolve_startup_dependencies(
            settings={
                "mode": settings.mode,
                "profile": settings.profile,
                "backends": {
                    "ui": settings.ui.backend,
                    "sync": settings.sync.backend,
                    "plugins": "builtin",
                },
            },
            environment={},
        )

    def launch_runtime(app, context):
        seen_context.append(context)
        return {"app": app, "trace_id": context.launch.trace_id}

    result = run_bootstrap(
        request=request,
        load_settings=load_settings,
        resolve_dependencies=resolve_dependencies,
        compose_runtime=compose_runtime,
        launch_runtime=launch_runtime,
        emit_event=events.append,
    )

    assert result.is_success is True
    assert result.context is seen_context[0]
    assert result.runtime_handle["trace_id"] == "trace-006"
    assert result.context.settings.profile == "ci"
    assert [event.name for event in events] == ["startup_started", "startup_succeeded"]
