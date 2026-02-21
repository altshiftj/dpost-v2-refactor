"""Unit coverage for infrastructure runtime bootstrap dependency helpers."""

from __future__ import annotations

from dataclasses import dataclass

import dpost.infrastructure.runtime.bootstrap_dependencies as deps
from dpost.infrastructure.runtime.ui_adapters import UiInteractionAdapter, UiTaskScheduler


@dataclass
class _PluginStub:
    """Plugin stub that exposes a pre-defined config object."""

    config: object

    def get_config(self) -> object:
        """Return the configured plugin settings object."""
        return self.config


def test_default_sync_manager_factory_assigns_interactions() -> None:
    """Attach provided interactions onto the default sync manager adapter."""

    class _SyncManagerStub:
        """Synthetic sync manager adapter with mutable interactions field."""

        def __init__(self) -> None:
            self.interactions = None

    original_cls = deps.KadiSyncAdapter
    deps.KadiSyncAdapter = _SyncManagerStub
    try:
        interactions = object()
        manager = deps.default_sync_manager_factory(interactions)
    finally:
        deps.KadiSyncAdapter = original_cls

    assert manager.interactions is interactions


def test_init_runtime_dirs_delegates_to_storage_initializer() -> None:
    """Call the shared storage directory initializer once."""
    calls = {"count": 0}

    original = deps.init_dirs
    deps.init_dirs = lambda: calls.__setitem__("count", calls["count"] + 1)
    try:
        deps.init_runtime_dirs()
    finally:
        deps.init_dirs = original

    assert calls["count"] == 1


def test_build_config_service_loads_plugins_and_initialises_service() -> None:
    """Load selected PC/device plugin configs and pass them to init_config."""
    pc_config = object()
    device_a = object()
    device_b = object()
    captured: dict[str, object] = {}
    result_service = object()

    original_load_pc = deps.load_pc_plugin
    original_load_device = deps.load_device_plugin
    original_init_config = deps.init_config
    deps.load_pc_plugin = lambda _pc: _PluginStub(pc_config)
    deps.load_device_plugin = (
        lambda name: _PluginStub(device_a if name == "dev-a" else device_b)
    )
    deps.init_config = (
        lambda pc, devices: captured.update({"pc": pc, "devices": list(devices)})
        or result_service
    )
    try:
        service = deps.build_config_service("pc-main", ("dev-a", "dev-b"))
    finally:
        deps.load_pc_plugin = original_load_pc
        deps.load_device_plugin = original_load_device
        deps.init_config = original_init_config

    assert service is result_service
    assert captured["pc"] is pc_config
    assert captured["devices"] == [device_a, device_b]


def test_build_interaction_adapter_wraps_ui_object() -> None:
    """Construct a UI interaction adapter for the provided runtime UI."""
    ui = object()
    adapter = deps.build_interaction_adapter(ui)

    assert isinstance(adapter, UiInteractionAdapter)
    assert adapter._ui is ui  # noqa: SLF001


def test_build_scheduler_wraps_ui_object() -> None:
    """Construct a UI-backed task scheduler for the provided runtime UI."""
    ui = object()
    scheduler = deps.build_scheduler(ui)

    assert isinstance(scheduler, UiTaskScheduler)
    assert scheduler._ui is ui  # noqa: SLF001


def test_build_watchdog_app_constructs_device_watchdog_app() -> None:
    """Pass composed runtime dependencies directly into watchdog app builder."""
    captured: dict[str, object] = {}
    sentinel_app = object()

    original_cls = deps.DeviceWatchdogApp
    deps.DeviceWatchdogApp = lambda **kwargs: captured.update(kwargs) or sentinel_app
    try:
        app = deps.build_watchdog_app(
            ui="ui",
            sync_manager="sync",
            config_service="config",
            interactions="interactions",
            scheduler="scheduler",
        )
    finally:
        deps.DeviceWatchdogApp = original_cls

    assert app is sentinel_app
    assert captured == {
        "ui": "ui",
        "sync_manager": "sync",
        "config_service": "config",
        "interactions": "interactions",
        "scheduler": "scheduler",
    }
