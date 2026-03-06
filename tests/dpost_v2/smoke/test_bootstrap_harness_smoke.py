from __future__ import annotations

from dpost_v2.application.startup.bootstrap import run_bootstrap
from dpost_v2.runtime.composition import compose_runtime


def test_bootstrap_smoke_runs_with_harness_fixtures(
    v2_bootstrap_request_factory,
    v2_startup_settings_factory,
    v2_startup_dependencies_factory,
    v2_now_utc,
) -> None:
    request = v2_bootstrap_request_factory()
    settings = v2_startup_settings_factory()
    dependencies = v2_startup_dependencies_factory()
    events = []

    result = run_bootstrap(
        request=request,
        load_settings=lambda _request: settings,
        resolve_dependencies=lambda _settings, _request: dependencies,
        compose_runtime=compose_runtime,
        launch_runtime=lambda runtime_handle, context: {
            "trace_id": context.launch.trace_id,
            "runtime_handle": runtime_handle,
        },
        emit_event=events.append,
        now_utc=v2_now_utc,
    )

    assert result.is_success is True
    assert result.failure is None
    assert result.runtime_handle["trace_id"] == request.trace_id
    assert [event.name for event in events] == ["startup_started", "startup_succeeded"]
