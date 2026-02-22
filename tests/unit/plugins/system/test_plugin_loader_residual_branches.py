"""Residual branch coverage for PluginLoader fallback/discovery paths."""

from __future__ import annotations

import importlib
import threading
import time
from types import ModuleType, SimpleNamespace

import pytest

from dpost.device_plugins.test_device.plugin import TestDevicePlugin
import dpost.plugins.system as plugin_system
from dpost.plugins.system import DEVICE_ENTRYPOINT_GROUP, PluginLoader, hookimpl


def _mapping_importer(mapping: dict[str, object]):
    """Return importer resolving configured modules before default imports."""

    def _importer(name: str) -> object:
        if name in mapping:
            return mapping[name]
        return importlib.import_module(name)

    return _importer


def _build_alias_device_module(alias: str) -> ModuleType:
    """Build module registering device plugin under provided alias."""
    module = ModuleType(f"fake.{alias}")

    @hookimpl
    def register_device_plugins(registry) -> None:
        registry.register(alias, TestDevicePlugin)

    module.register_device_plugins = register_device_plugins
    return module


def test_load_device_triggers_builtin_fallback_when_registry_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invoke builtin loader when lazy loading fails and registry is empty."""
    loader = PluginLoader(load_entrypoints=False, load_builtins=False)
    calls = {"builtin": 0, "create": 0}

    def fake_create(_name: str):
        calls["create"] += 1
        raise RuntimeError("missing")

    monkeypatch.setattr(loader._device_registry, "create", fake_create)
    monkeypatch.setattr(loader, "_lazy_load_builtin", lambda *_args: False)
    monkeypatch.setattr(loader, "_lazy_load_entrypoint", lambda *_args: False)
    monkeypatch.setattr(
        loader,
        "_load_builtin_plugins",
        lambda: calls.__setitem__("builtin", calls["builtin"] + 1),
    )

    with pytest.raises(RuntimeError, match="missing"):
        loader.load_device("missing_device")

    assert calls["builtin"] == 1
    assert calls["create"] == 2


def test_load_builtin_plugins_skips_packages_without_path_attribute() -> None:
    """Skip package iteration when imported package lacks __path__ metadata."""
    iter_calls = {"count": 0}
    importer = _mapping_importer(
        {
            "dpost.device_plugins": SimpleNamespace(),
            "dpost.pc_plugins": SimpleNamespace(),
        }
    )

    def fake_iter_modules(_path, *, prefix):
        _ = prefix
        iter_calls["count"] += 1
        return []

    loader = PluginLoader(
        load_entrypoints=False,
        load_builtins=False,
        module_importer=importer,
        iter_modules_fn=fake_iter_modules,
    )

    loader._load_builtin_plugins()

    assert iter_calls["count"] == 0


def test_lazy_load_entrypoint_skips_nonmatching_entries_before_match() -> None:
    """Continue scanning entry points until matching alias is found."""
    loader = PluginLoader(
        load_entrypoints=False,
        load_builtins=False,
        module_importer=_mapping_importer(
            {"fake.alias_device": _build_alias_device_module("alias_device")}
        ),
        iter_entry_points_fn=lambda group: [
            SimpleNamespace(name="other", value="fake.other"),
            SimpleNamespace(name="alias_device", value="fake.alias_device"),
        ]
        if group == DEVICE_ENTRYPOINT_GROUP
        else [],
    )

    loaded = loader._lazy_load_entrypoint(DEVICE_ENTRYPOINT_GROUP, "alias_device")

    assert loaded is True
    assert "alias_device" in loader.available_device_plugins()


def test_iter_entry_points_uses_select_api_for_py310_plus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use modern entry-point selection API when running on Python 3.10+."""
    called: list[str] = []

    class _EPs:
        def select(self, *, group: str):
            called.append(group)
            return ["a", "b"]

    monkeypatch.setattr(plugin_system.sys, "version_info", (3, 10, 0))
    monkeypatch.setattr(plugin_system, "entry_points", lambda: _EPs())

    resolved = list(plugin_system._iter_entry_points("example.group"))

    assert resolved == ["a", "b"]
    assert called == ["example.group"]


def test_get_plugin_loader_initializes_singleton_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create plugin loader singleton once and reuse on repeated access."""
    created: list[object] = []

    class _LoaderStub:
        def __init__(self, **kwargs) -> None:
            created.append(kwargs)

    monkeypatch.setattr(plugin_system, "_PLUGIN_LOADER_SINGLETON", None)
    monkeypatch.setattr(plugin_system, "PluginLoader", _LoaderStub)

    first = plugin_system.get_plugin_loader()
    second = plugin_system.get_plugin_loader()

    assert first is second
    assert created == [{"load_entrypoints": False, "load_builtins": False}]


def test_loader_uses_reentrant_lock_for_nested_discovery_operations() -> None:
    """Nested loader operations should re-enter the same lock without blocking."""

    class _TrackingRLock:
        def __init__(self) -> None:
            self.depth = 0
            self.max_depth = 0
            self.enter_count = 0

        def __enter__(self):
            self.depth += 1
            self.enter_count += 1
            self.max_depth = max(self.max_depth, self.depth)
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            _ = (exc_type, exc, tb)
            self.depth -= 1

    loader = PluginLoader(
        load_entrypoints=False,
        load_builtins=False,
        iter_entry_points_fn=lambda _group: [],
    )
    tracking_lock = _TrackingRLock()
    loader._lock = tracking_lock

    loader._load_entrypoints(DEVICE_ENTRYPOINT_GROUP)

    assert tracking_lock.depth == 0
    assert tracking_lock.enter_count >= 2
    assert tracking_lock.max_depth >= 2


def test_get_plugin_loader_initialization_is_serialized_under_thread_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent singleton access should not construct multiple loaders."""
    created: list[dict[str, object]] = []
    results: list[object] = []
    start_barrier = threading.Barrier(4)

    class _LoaderStub:
        def __init__(self, **kwargs) -> None:
            created.append(kwargs)
            time.sleep(0.02)

    def _worker() -> None:
        start_barrier.wait()
        results.append(plugin_system.get_plugin_loader())

    monkeypatch.setattr(plugin_system, "_PLUGIN_LOADER_SINGLETON", None)
    monkeypatch.setattr(plugin_system, "PluginLoader", _LoaderStub)

    threads = [threading.Thread(target=_worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(created) == 1
    assert len(results) == 4
    assert all(result is results[0] for result in results)
