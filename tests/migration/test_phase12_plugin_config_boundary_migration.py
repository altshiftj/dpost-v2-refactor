"""Migration tests for Phase 12 plugin/config boundary migration."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_COMPOSITION_PATH = PROJECT_ROOT / "src" / "dpost" / "runtime" / "composition.py"


def _reload_composition_module() -> ModuleType:
    """Reload dpost composition module with a clean import state."""
    sys.modules.pop("dpost.runtime.composition", None)
    return importlib.import_module("dpost.runtime.composition")


def test_runtime_composition_has_no_direct_plugin_config_env_resolution() -> None:
    """Require plugin/config env resolution to move out of runtime composition."""
    composition_contents = DPOST_COMPOSITION_PATH.read_text(encoding="utf-8")

    assert "DPOST_PLUGIN_PROFILE" not in composition_contents
    assert "DPOST_PC_NAME" not in composition_contents
    assert "DPOST_DEVICE_PLUGINS" not in composition_contents
    assert "DPOST_PROMETHEUS_PORT" not in composition_contents
    assert "DPOST_OBSERVABILITY_PORT" not in composition_contents


def test_compose_bootstrap_uses_plugin_and_config_boundary_resolvers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require composition to delegate plugin/config resolution to boundary modules."""
    composition = _reload_composition_module()

    sync_adapter = object()
    plugin_profile = SimpleNamespace(pc_name="profile_pc", device_names=("dev-a",))
    resolved_settings = SimpleNamespace(
        pc_name="resolved_pc",
        device_names=("dev-b",),
        prometheus_port=9700,
        observability_port=9701,
        env_source=None,
    )
    expected_context = SimpleNamespace(app=SimpleNamespace(run=lambda: None))
    captured: dict[str, object] = {}

    monkeypatch.setattr(composition, "select_sync_adapter", lambda: sync_adapter)
    monkeypatch.setattr(composition, "select_runtime_mode", lambda: "headless")
    monkeypatch.setattr(
        composition,
        "resolve_plugin_profile_selection",
        lambda **_kwargs: plugin_profile,
    )
    monkeypatch.setattr(
        composition,
        "resolve_runtime_startup_settings",
        lambda **_kwargs: resolved_settings,
    )

    def fake_compose_runtime_context(**kwargs: object) -> object:
        captured.update(kwargs)
        return expected_context

    monkeypatch.setattr(
        composition, "compose_runtime_context", fake_compose_runtime_context
    )

    context = composition.compose_bootstrap()

    assert context is expected_context
    assert captured["plugin_profile"] is plugin_profile
    assert captured["resolved_settings"] is resolved_settings


def test_plugin_profile_boundary_keeps_actionable_unknown_profile_error() -> None:
    """Require plugin profile boundary to keep actionable unknown-profile errors."""
    from ipat_watchdog.core.app.bootstrap import StartupError

    from dpost.plugins.profile_selection import resolve_plugin_profile_selection

    with pytest.raises(StartupError, match="Unknown plugin profile"):
        resolve_plugin_profile_selection(
            profile_name="missing-profile",
            startup_error_factory=StartupError,
        )
