"""Migration tests for Phase 10 runtime orchestration extraction."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest


def _reload_composition_module() -> ModuleType:
    """Reload dpost composition module with a clean import state."""
    sys.modules.pop("dpost.runtime.composition", None)
    return importlib.import_module("dpost.runtime.composition")


@pytest.fixture(autouse=True)
def _clear_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear startup-related env vars before each test."""
    for key in (
        "DPOST_RUNTIME_MODE",
        "DPOST_SYNC_ADAPTER",
        "DPOST_PLUGIN_PROFILE",
        "DPOST_PC_NAME",
        "DPOST_DEVICE_PLUGINS",
        "DPOST_PROMETHEUS_PORT",
        "DPOST_OBSERVABILITY_PORT",
    ):
        monkeypatch.delenv(key, raising=False)


def test_compose_bootstrap_delegates_to_application_orchestration_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require composition to delegate runtime orchestration through application."""
    composition = _reload_composition_module()

    sync_adapter = object()
    plugin_profile = SimpleNamespace(pc_name="profile_pc", device_names=("dev-a",))
    resolved_settings = SimpleNamespace(
        pc_name="resolved_pc",
        device_names=("dev-b",),
        prometheus_port=9400,
        observability_port=9401,
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
    assert captured["sync_adapter"] is sync_adapter
    assert captured["plugin_profile"] is plugin_profile
    assert captured["runtime_mode"] == "headless"
    assert captured["resolved_settings"] is resolved_settings
    assert captured["ui_factory_selector"] is composition.select_ui_factory
    assert captured["startup_settings_builder"] is composition.build_startup_settings
    assert captured["runtime_bootstrap"] is composition.bootstrap_runtime


def test_application_runtime_orchestration_prefers_profile_settings_over_env() -> None:
    """Require application orchestration to prioritize profile startup settings."""
    from dpost.application.services.runtime_startup import compose_runtime_context

    sync_adapter = object()
    plugin_profile = SimpleNamespace(
        pc_name="profile_pc",
        device_names=("profile-device-a", "profile-device-b"),
    )
    resolved_settings = SimpleNamespace(
        pc_name="resolved_pc",
        device_names=("resolved-device",),
        prometheus_port=9500,
        observability_port=9501,
        env_source="env",
    )
    captured: dict[str, object] = {}

    def fake_ui_factory_selector(mode_name: str) -> object:
        captured["mode_name"] = mode_name
        return object()

    def fake_startup_settings_builder(**kwargs: object) -> object:
        captured["settings_kwargs"] = kwargs
        return SimpleNamespace(**kwargs)

    def fake_runtime_bootstrap(**kwargs: object) -> object:
        captured["bootstrap_kwargs"] = kwargs
        return "context"

    context = compose_runtime_context(
        sync_adapter=sync_adapter,
        plugin_profile=plugin_profile,
        runtime_mode="desktop",
        resolved_settings=resolved_settings,
        ui_factory_selector=fake_ui_factory_selector,
        startup_settings_builder=fake_startup_settings_builder,
        runtime_bootstrap=fake_runtime_bootstrap,
    )

    assert context == "context"
    assert captured["mode_name"] == "desktop"
    assert captured["settings_kwargs"] == {
        "pc_name": "profile_pc",
        "device_names": ("profile-device-a", "profile-device-b"),
    }
    bootstrap_kwargs = captured["bootstrap_kwargs"]
    assert bootstrap_kwargs["settings"].pc_name == "profile_pc"
    assert bootstrap_kwargs["sync_manager_factory"](object()) is sync_adapter


def test_application_runtime_orchestration_uses_resolved_settings_without_profile() -> (
    None
):
    """Require application orchestration to preserve env/explicit resolved settings."""
    from dpost.application.services.runtime_startup import compose_runtime_context

    sync_adapter = object()
    resolved_settings = SimpleNamespace(
        pc_name="resolved_pc",
        device_names=("resolved-device",),
        prometheus_port=9510,
        observability_port=9511,
        env_source="env",
    )
    captured: dict[str, object] = {}

    def fake_runtime_bootstrap(**kwargs: object) -> object:
        captured["bootstrap_kwargs"] = kwargs
        return "context"

    context = compose_runtime_context(
        sync_adapter=sync_adapter,
        plugin_profile=None,
        runtime_mode="headless",
        resolved_settings=resolved_settings,
        ui_factory_selector=lambda _mode: object(),
        startup_settings_builder=lambda **kwargs: SimpleNamespace(**kwargs),
        runtime_bootstrap=fake_runtime_bootstrap,
    )

    assert context == "context"
    bootstrap_kwargs = captured["bootstrap_kwargs"]
    assert bootstrap_kwargs["settings"] is resolved_settings
    assert bootstrap_kwargs["sync_manager_factory"](object()) is sync_adapter
