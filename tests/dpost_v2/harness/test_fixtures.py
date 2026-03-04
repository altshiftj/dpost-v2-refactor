from __future__ import annotations

from pathlib import Path

from dpost_v2.application.startup.bootstrap import BootstrapRequest


def test_v2_trace_id_factory_is_deterministic(v2_trace_id_factory) -> None:
    assert v2_trace_id_factory() == "trace-0001"
    assert v2_trace_id_factory() == "trace-0002"
    assert v2_trace_id_factory() == "trace-0003"


def test_v2_bootstrap_request_factory_increments_trace_ids(
    v2_bootstrap_request_factory,
) -> None:
    first = v2_bootstrap_request_factory()
    second = v2_bootstrap_request_factory(mode="desktop", profile="ops")

    assert isinstance(first, BootstrapRequest)
    assert isinstance(second, BootstrapRequest)
    assert first.trace_id == "trace-0001"
    assert second.trace_id == "trace-0002"
    assert second.mode == "desktop"
    assert second.profile == "ops"


def test_v2_startup_settings_factory_uses_workspace_root(
    v2_startup_settings_factory,
    v2_workspace_root: Path,
) -> None:
    settings = v2_startup_settings_factory()
    root = (v2_workspace_root / "runtime").resolve()

    assert Path(settings.paths.root) == root
    assert Path(settings.paths.watch) == root / "incoming"
    assert Path(settings.paths.dest) == root / "processed"
    assert Path(settings.paths.staging) == root / "tmp"


def test_v2_startup_context_factory_uses_deterministic_metadata(
    v2_startup_context_factory,
) -> None:
    context = v2_startup_context_factory()

    assert context.launch.trace_id == "trace-0001"
    assert context.launch.process_id == 4242
    assert context.launch.boot_timestamp_utc == "2026-03-04T12:00:00+00:00"
