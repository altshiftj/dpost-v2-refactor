from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from dpost_v2.application.startup import bootstrap as bootstrap_module
from dpost_v2.application.startup.bootstrap import BootstrapRequest, run_bootstrap
from dpost_v2.application.startup.settings_service import (
    SettingsLoadFailure,
    SettingsLoadResult,
    load_startup_settings,
)
from dpost_v2.runtime.composition import CompositionBundle, compose_runtime
from dpost_v2.runtime.startup_dependencies import (
    StartupDependencies,
    resolve_startup_dependencies,
)


@dataclass(frozen=True)
class FakeSettings:
    mode: str = "headless"
    profile: str = "ci"


@dataclass(frozen=True)
class FakeRunSettings:
    mode: str = "headless"
    profile: str = "ci"

    def to_dependency_payload(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "profile": self.profile,
            "backends": {
                "ui": "headless",
                "sync": "noop",
                "plugins": "builtin",
                "observability": "structured",
                "storage": "filesystem",
            },
        }


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
            runtime_handle="composed-runtime-handle",
            port_bindings={"ui": object(), "event_sink": object()},
            diagnostics={"ui_backend": "headless"},
            shutdown_all=lambda: stage_calls.append("composition_shutdown"),
        )

    def launch_runtime(runtime_handle, context):
        stage_calls.append("launch")
        assert runtime_handle == "composed-runtime-handle"
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
            runtime_handle=DummyApp(),
            port_bindings={"ui": object(), "event_sink": object()},
            diagnostics={},
            shutdown_all=lambda: cleanup_calls.append("composition_shutdown"),
        )

    def launch_runtime(_runtime_handle, _context):
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


def test_bootstrap_integration_with_settings_service_and_runtime_modules(
    tmp_path,
) -> None:
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

    def launch_runtime(runtime_handle, context):
        seen_context.append(context)
        return {"runtime_handle": runtime_handle, "trace_id": context.launch.trace_id}

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


def test_bootstrap_started_event_includes_request_metadata() -> None:
    request = BootstrapRequest(
        mode="headless",
        profile="ci",
        trace_id="trace-007",
        metadata={"source": "cli", "attempt": 2},
    )
    events = []
    settings = FakeSettings()
    dependencies = _dependencies()

    result = run_bootstrap(
        request=request,
        load_settings=lambda _request: settings,
        resolve_dependencies=lambda _settings, _request: dependencies,
        compose_runtime=lambda _context: CompositionBundle(
            app=DummyApp(),
            runtime_handle=DummyApp(),
            port_bindings={"ui": object(), "event_sink": object()},
            diagnostics={},
            shutdown_all=lambda: None,
        ),
        launch_runtime=lambda runtime_handle, _context: runtime_handle,
        emit_event=events.append,
    )

    assert result.is_success is True
    assert events[0].name == "startup_started"
    assert events[0].payload["metadata"] == {"source": "cli", "attempt": 2}


def test_bootstrap_success_event_includes_request_metadata_and_boot_timestamp() -> None:
    fixed_now = datetime(2026, 3, 5, 9, 15, tzinfo=UTC)
    request = BootstrapRequest(
        mode="headless",
        profile="ci",
        trace_id="trace-008a",
        metadata={"headless": True, "dry_run": False},
    )
    events = []
    settings = FakeSettings()
    dependencies = _dependencies()

    result = run_bootstrap(
        request=request,
        load_settings=lambda _request: settings,
        resolve_dependencies=lambda _settings, _request: dependencies,
        compose_runtime=lambda _context: CompositionBundle(
            app=DummyApp(),
            runtime_handle=DummyApp(),
            port_bindings={"ui": object(), "event_sink": object()},
            diagnostics={},
            shutdown_all=lambda: None,
        ),
        launch_runtime=lambda runtime_handle, _context: runtime_handle,
        emit_event=events.append,
        now_utc=lambda: fixed_now,
    )

    assert result.is_success is True
    assert [event.name for event in events] == ["startup_started", "startup_succeeded"]
    assert events[1].payload["metadata"] == {"headless": True, "dry_run": False}
    assert events[1].payload["boot_timestamp_utc"] == "2026-03-05T09:15:00+00:00"


def test_bootstrap_emits_stable_diagnostics_fields_on_success() -> None:
    request = BootstrapRequest(mode="v2", profile="ci", trace_id="trace-009")
    events = []

    loaded_settings = SettingsLoadResult(
        is_success=True,
        settings=FakeSettings(mode="headless", profile="ops"),
        provenance={
            "mode": "cli",
            "profile": "file",
            "ui.backend": "defaults",
            "sync.backend": "environment",
        },
        fingerprint="fingerprint-009",
    )
    dependencies = StartupDependencies(
        factories={
            "observability": lambda: {"kind": "observability"},
            "storage": lambda: {"kind": "storage"},
            "filesystem": lambda: {"kind": "filesystem"},
            "clock": lambda: {"kind": "clock"},
            "sync": lambda: {"kind": "sync"},
            "ui": lambda: {"kind": "ui"},
            "event_sink": lambda: {"kind": "event_sink"},
            "plugins": lambda: {"kind": "plugins"},
        },
        selected_backends={
            "ui": "headless",
            "sync": "noop",
            "plugins": "builtin",
            "observability": "structured",
            "storage": "filesystem",
        },
        lazy_factories=frozenset({"sync", "plugins"}),
        warnings=(),
        cleanup=None,
    )

    result = run_bootstrap(
        request=request,
        load_settings=lambda _request: loaded_settings,
        resolve_dependencies=lambda _settings, _request: dependencies,
        compose_runtime=lambda _context: CompositionBundle(
            app=DummyApp(),
            runtime_handle=DummyApp(),
            port_bindings={"plugins": object(), "event_sink": object()},
            diagnostics={
                "plugin_visibility": "bound",
                "plugin_backend": "builtin",
                "selected_backends": {"plugins": "builtin"},
            },
            shutdown_all=lambda: None,
        ),
        launch_runtime=lambda runtime_handle, _context: runtime_handle,
        emit_event=events.append,
    )

    assert result.is_success is True
    assert [event.name for event in events] == ["startup_started", "startup_succeeded"]

    common_keys = {
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
    }
    started_payload = events[0].payload
    succeeded_payload = events[1].payload

    assert common_keys <= set(started_payload)
    assert common_keys <= set(succeeded_payload)
    assert started_payload["requested_mode"] == "v2"
    assert started_payload["mode"] == "v2"
    assert started_payload["selected_backends"] == {}
    assert started_payload["plugin_backend"] is None
    assert started_payload["plugin_visibility"] == "unknown"
    assert succeeded_payload["mode"] == "headless"
    assert succeeded_payload["profile"] == "ops"
    assert succeeded_payload["settings_fingerprint"] == "fingerprint-009"
    assert succeeded_payload["settings_provenance"]["mode"] == "cli"
    assert succeeded_payload["selected_backends"]["plugins"] == "builtin"
    assert succeeded_payload["plugin_backend"] == "builtin"
    assert succeeded_payload["plugin_visibility"] == "bound"


def test_bootstrap_failure_event_includes_request_metadata() -> None:
    fixed_now = datetime(2026, 3, 5, 9, 30, tzinfo=UTC)
    request = BootstrapRequest(
        mode="headless",
        profile="ci",
        trace_id="trace-010a",
        metadata={"headless": True, "dry_run": True},
    )
    events = []
    settings = FakeSettings()

    result = run_bootstrap(
        request=request,
        load_settings=lambda _request: settings,
        resolve_dependencies=lambda _settings, _request: _dependencies(),
        compose_runtime=lambda _context: (_ for _ in ()).throw(
            RuntimeError("composition failed")
        ),
        launch_runtime=lambda _app, _context: "unused",
        emit_event=events.append,
        now_utc=lambda: fixed_now,
    )

    assert result.is_success is False
    assert result.failure is not None
    assert [event.name for event in events] == ["startup_started", "startup_failed"]
    assert events[1].payload["metadata"] == {"headless": True, "dry_run": True}
    assert events[1].payload["boot_timestamp_utc"] == "2026-03-05T09:30:00+00:00"


def test_bootstrap_failed_event_preserves_diagnostics_snapshot() -> None:
    request = BootstrapRequest(mode="headless", profile="ci", trace_id="trace-010")
    events = []
    loaded_settings = SettingsLoadResult(
        is_success=True,
        settings=FakeSettings(mode="headless", profile="ci"),
        provenance={"mode": "cli", "profile": "cli"},
        fingerprint="fingerprint-010",
    )
    dependencies = StartupDependencies(
        factories={
            "observability": lambda: {"kind": "observability"},
            "storage": lambda: {"kind": "storage"},
            "filesystem": lambda: {"kind": "filesystem"},
            "clock": lambda: {"kind": "clock"},
            "sync": lambda: {"kind": "sync"},
            "ui": lambda: {"kind": "ui"},
            "event_sink": lambda: {"kind": "event_sink"},
            "plugins": lambda: {"kind": "plugins"},
        },
        selected_backends={
            "ui": "headless",
            "sync": "noop",
            "plugins": "builtin",
            "observability": "structured",
            "storage": "filesystem",
        },
        lazy_factories=frozenset({"sync", "plugins"}),
        warnings=(),
        cleanup=None,
    )

    result = run_bootstrap(
        request=request,
        load_settings=lambda _request: loaded_settings,
        resolve_dependencies=lambda _settings, _request: dependencies,
        compose_runtime=lambda _context: (_ for _ in ()).throw(
            RuntimeError("composition broke")
        ),
        launch_runtime=lambda _app, _context: "unused",
        emit_event=events.append,
    )

    assert result.is_success is False
    assert [event.name for event in events] == ["startup_started", "startup_failed"]
    failed_payload = events[1].payload
    assert failed_payload["stage"] == "composition"
    assert failed_payload["error_type"] == "RuntimeError"
    assert failed_payload["settings_fingerprint"] == "fingerprint-010"
    assert failed_payload["settings_provenance"]["profile"] == "cli"
    assert failed_payload["selected_backends"]["plugins"] == "builtin"
    assert failed_payload["plugin_backend"] == "builtin"
    assert failed_payload["plugin_visibility"] == "configured"


@pytest.mark.parametrize("dry_run", [False, True])
def test_bootstrap_cleanup_order_is_stable_for_dry_run_and_non_dry_run(
    dry_run: bool,
) -> None:
    request = BootstrapRequest(
        mode="headless",
        profile="ci",
        trace_id=f"trace-011-{'dry' if dry_run else 'live'}",
        metadata={"headless": True, "dry_run": dry_run},
    )
    cleanup_calls: list[str] = []

    def load_settings(_request):
        return FakeSettings()

    def resolve_dependencies(_settings, _request):
        return _dependencies(cleanup=lambda: cleanup_calls.append("deps_cleanup"))

    def compose(_context):
        return CompositionBundle(
            app=DummyApp(),
            runtime_handle=DummyApp(),
            port_bindings={"ui": object(), "event_sink": object()},
            diagnostics={},
            shutdown_all=lambda: cleanup_calls.append("composition_shutdown"),
        )

    def launch_runtime(_runtime_handle, _context):
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


def test_run_uses_process_environment_when_override_not_supplied(monkeypatch) -> None:
    request = BootstrapRequest(mode="headless", profile="ci", trace_id="trace-008")
    events = []
    captured_environment: dict[str, str] = {}
    settings = FakeRunSettings()

    monkeypatch.setenv("DPOST_BOOTSTRAP_TEST_TOKEN", "present")

    def fake_load_startup_settings(_request, *, root_hint, cache):
        return SettingsLoadResult(is_success=True, settings=settings)

    def fake_resolve_startup_dependencies(*, settings, environment):
        captured_environment.update(environment)
        return StartupDependencies(
            factories={
                "observability": lambda: {"kind": "observability"},
                "storage": lambda: {"kind": "storage", "backend": "filesystem"},
                "sync": lambda: {"kind": "sync", "backend": "noop"},
                "ui": lambda: {"kind": "ui", "backend": "headless"},
                "event_sink": lambda: {"kind": "event_sink"},
                "plugins": lambda: {"kind": "plugins"},
                "clock": lambda: {"kind": "clock"},
                "filesystem": lambda: {"kind": "filesystem"},
            },
            selected_backends={
                "ui": "headless",
                "sync": "noop",
                "plugins": "builtin",
                "observability": "structured",
                "storage": "filesystem",
            },
            lazy_factories=frozenset(),
            warnings=(),
            cleanup=None,
        )

    monkeypatch.setattr(
        bootstrap_module,
        "load_startup_settings",
        fake_load_startup_settings,
    )
    monkeypatch.setattr(
        bootstrap_module,
        "resolve_startup_dependencies_root",
        fake_resolve_startup_dependencies,
    )

    result = bootstrap_module.run(request=request, emit_event=events.append)

    assert result.is_success is True
    assert captured_environment["DPOST_BOOTSTRAP_TEST_TOKEN"] == "present"
