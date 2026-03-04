from __future__ import annotations

from pathlib import Path

from dpost_v2.application.contracts.context import RuntimeContext
from dpost_v2.application.startup.bootstrap import BootstrapRequest
from dpost_v2.runtime.startup_dependencies import StartupDependencies
from tests.dpost_v2._support.factories import (
    build_bootstrap_request,
    build_runtime_context,
    build_startup_context,
    build_startup_dependencies,
    build_startup_settings,
)


def test_build_bootstrap_request_uses_deterministic_defaults() -> None:
    request = build_bootstrap_request()

    assert isinstance(request, BootstrapRequest)
    assert request.mode == "headless"
    assert request.profile == "ci"
    assert request.trace_id == "trace-0001"
    assert dict(request.metadata) == {}


def test_build_startup_settings_normalizes_paths_from_root_hint(tmp_path: Path) -> None:
    settings = build_startup_settings(root_hint=tmp_path)
    root = (tmp_path / "runtime").resolve()

    assert settings.mode == "headless"
    assert settings.profile == "ci"
    assert Path(settings.paths.root) == root
    assert Path(settings.paths.watch) == root / "incoming"
    assert Path(settings.paths.dest) == root / "processed"
    assert Path(settings.paths.staging) == root / "tmp"


def test_build_startup_dependencies_exposes_default_ports() -> None:
    dependencies = build_startup_dependencies()

    assert isinstance(dependencies, StartupDependencies)
    assert set(dependencies.factories) >= {
        "observability",
        "storage",
        "sync",
        "ui",
        "event_sink",
        "plugins",
    }
    assert dependencies.selected_backends["ui"] == "headless"
    assert dependencies.selected_backends["sync"] == "noop"


def test_build_startup_context_uses_deterministic_launch_metadata(
    tmp_path: Path,
) -> None:
    context = build_startup_context(root_hint=tmp_path)

    assert context.launch.requested_mode == "headless"
    assert context.launch.requested_profile == "ci"
    assert context.launch.trace_id == "trace-0001"
    assert context.launch.process_id == 4242
    assert context.launch.boot_timestamp_utc == "2026-03-04T12:00:00+00:00"


def test_build_runtime_context_uses_stable_defaults() -> None:
    context = build_runtime_context()

    assert isinstance(context, RuntimeContext)
    assert context.mode == "headless"
    assert context.profile == "ci"
    assert context.session_id == "session-0001"
    assert context.event_id == "event-0001"
    assert context.trace_id == "trace-0001"
    assert dict(context.dependency_ids) == {
        "clock": "clock:default",
        "sync": "sync:default",
        "ui": "ui:default",
    }
