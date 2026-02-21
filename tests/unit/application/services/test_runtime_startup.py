"""Unit coverage for application runtime-startup orchestration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dpost.application.services.runtime_startup import compose_runtime_context
from dpost.plugins.reference import PluginProfile


@dataclass
class _SyncAdapterStub:
    """Minimal sync adapter stub for runtime-startup composition tests."""

    def sync_record_to_database(self, local_record: object) -> bool:
        """Implement sync port contract with deterministic true response."""
        return True


def test_compose_runtime_context_uses_profile_to_build_settings() -> None:
    """Build startup settings from plugin profile when a profile is supplied."""
    sync_adapter = _SyncAdapterStub()
    profile = PluginProfile(pc_name="pc-profile", device_names=("device-a",))
    captured_bootstrap_kwargs: dict[str, object] = {}
    builder_calls: list[dict[str, object]] = []

    def _ui_factory_selector(mode_name: str | None = None):  # type: ignore[no-untyped-def]
        assert mode_name == "headless"
        return "ui-factory"

    def _startup_settings_builder(**kwargs: object) -> object:
        builder_calls.append(dict(kwargs))
        return {"built": kwargs}

    def _runtime_bootstrap(**kwargs: object) -> object:
        captured_bootstrap_kwargs.update(kwargs)
        return {"context": "bootstrapped"}

    context = compose_runtime_context(
        sync_adapter=sync_adapter,
        plugin_profile=profile,
        runtime_mode="headless",
        resolved_settings=None,
        ui_factory_selector=_ui_factory_selector,
        startup_settings_builder=_startup_settings_builder,
        runtime_bootstrap=_runtime_bootstrap,
    )

    assert context == {"context": "bootstrapped"}
    assert builder_calls == [
        {"pc_name": "pc-profile", "device_names": ("device-a",)},
    ]
    assert captured_bootstrap_kwargs["ui_factory"] == "ui-factory"
    sync_factory = captured_bootstrap_kwargs["sync_manager_factory"]
    assert callable(sync_factory)
    assert sync_factory(object()) is sync_adapter
    assert captured_bootstrap_kwargs["settings"] == {
        "built": {"pc_name": "pc-profile", "device_names": ("device-a",)}
    }


def test_compose_runtime_context_uses_resolved_settings_when_no_profile() -> None:
    """Pass through resolved settings when plugin profile selection is absent."""
    sync_adapter = _SyncAdapterStub()
    resolved_settings = object()
    captured_bootstrap_kwargs: dict[str, Any] = {}

    def _runtime_bootstrap(**kwargs: object) -> object:
        captured_bootstrap_kwargs.update(kwargs)
        return "context"

    context = compose_runtime_context(
        sync_adapter=sync_adapter,
        plugin_profile=None,
        runtime_mode="desktop",
        resolved_settings=resolved_settings,
        ui_factory_selector=lambda _mode=None: "desktop-ui",
        startup_settings_builder=lambda **_kwargs: {"unused": True},
        runtime_bootstrap=_runtime_bootstrap,
    )

    assert context == "context"
    assert captured_bootstrap_kwargs["settings"] is resolved_settings


def test_compose_runtime_context_omits_settings_when_none_available() -> None:
    """Do not include settings when neither profile nor resolved settings exist."""
    sync_adapter = _SyncAdapterStub()
    captured_bootstrap_kwargs: dict[str, Any] = {}

    def _runtime_bootstrap(**kwargs: object) -> object:
        captured_bootstrap_kwargs.update(kwargs)
        return "context"

    context = compose_runtime_context(
        sync_adapter=sync_adapter,
        plugin_profile=None,
        runtime_mode="headless",
        resolved_settings=None,
        ui_factory_selector=lambda _mode=None: "headless-ui",
        startup_settings_builder=lambda **_kwargs: {"unused": True},
        runtime_bootstrap=_runtime_bootstrap,
    )

    assert context == "context"
    assert "settings" not in captured_bootstrap_kwargs
