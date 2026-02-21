from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType, SimpleNamespace

import pluggy
import pytest

import dpost.plugins.system as plugin_system
from dpost.device_plugins.test_device.plugin import TestDevicePlugin
from dpost.pc_plugins.test_pc.plugin import TestPCPlugin
from dpost.plugins.system import (
    DEVICE_ENTRYPOINT_GROUP,
    PC_ENTRYPOINT_GROUP,
    DevicePluginRegistry,
    PCPluginRegistry,
    PluginLoader,
    hookimpl,
)


def _mapping_importer(mapping: dict[str, object]):
    """Return an importer that resolves from mapping before default importlib."""

    def _importer(name: str) -> object:
        if name in mapping:
            return mapping[name]
        return importlib.import_module(name)

    return _importer


def _build_alias_device_module(alias: str = "alias_device") -> ModuleType:
    """Build a plugin module that registers a device plugin under alias."""

    module = ModuleType(f"fake.{alias}")

    @hookimpl
    def register_device_plugins(registry) -> None:
        registry.register(alias, TestDevicePlugin)

    module.register_device_plugins = register_device_plugins
    return module


def _build_alias_pc_module(alias: str = "alias_pc") -> ModuleType:
    """Build a plugin module that registers a PC plugin under alias."""

    module = ModuleType(f"fake.{alias}")

    @hookimpl
    def register_pc_plugins(registry) -> None:
        registry.register(alias, TestPCPlugin)

    module.register_pc_plugins = register_pc_plugins
    return module


def test_registry_rejects_empty_name() -> None:
    registry = DevicePluginRegistry()

    with pytest.raises(ValueError, match="must not be empty"):
        registry.register("   ", TestDevicePlugin)


def test_device_registry_create_rejects_non_device_plugin_factory() -> None:
    registry = DevicePluginRegistry()
    registry.register("bad", lambda: object())

    with pytest.raises(TypeError, match="expected DevicePlugin"):
        registry.create("bad")


def test_pc_registry_create_rejects_non_pc_plugin_factory() -> None:
    registry = PCPluginRegistry()
    registry.register("bad", lambda: object())

    with pytest.raises(TypeError, match="expected PCPlugin"):
        registry.create("bad")


def test_register_plugin_wraps_pluggy_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    loader = PluginLoader(load_entrypoints=False, load_builtins=False)

    def _raise_validation_error(*_args, **_kwargs):
        raise pluggy.PluginValidationError("plugin", "invalid")

    monkeypatch.setattr(loader._pm, "register", _raise_validation_error)

    with pytest.raises(RuntimeError, match="failed validation"):
        loader.register_plugin(object(), name="bad-plugin")


def test_loader_init_with_load_flags_uses_injected_discovery_seams() -> None:
    counts = {"entrypoint_calls": 0, "iter_modules_calls": 0}

    def _iter_entry_points(_group: str):
        counts["entrypoint_calls"] += 1
        return []

    def _iter_modules(_path, *, prefix):
        _ = prefix
        counts["iter_modules_calls"] += 1
        return []

    package = SimpleNamespace(__path__=["dummy"])
    importer = _mapping_importer(
        {
            "dpost.device_plugins": package,
            "dpost.pc_plugins": package,
        }
    )

    PluginLoader(
        load_entrypoints=True,
        load_builtins=True,
        module_importer=importer,
        iter_modules_fn=_iter_modules,
        iter_entry_points_fn=_iter_entry_points,
    )

    assert counts["entrypoint_calls"] == 2
    assert counts["iter_modules_calls"] == 2


def test_load_entrypoints_registers_alias_module_from_injected_discovery() -> None:
    alias_module = _build_alias_device_module("alias_device")
    loader = PluginLoader(
        load_entrypoints=False,
        load_builtins=False,
        module_importer=_mapping_importer({"fake.alias_device": alias_module}),
        iter_entry_points_fn=lambda group: [
            SimpleNamespace(name="alias_device", value="fake.alias_device")
        ]
        if group == DEVICE_ENTRYPOINT_GROUP
        else [],
    )

    loader._load_entrypoints(DEVICE_ENTRYPOINT_GROUP)

    assert "alias_device" in loader.available_device_plugins()


def test_load_builtin_plugins_handles_import_failure_gracefully() -> None:
    def _importer(name: str) -> object:
        raise ModuleNotFoundError(name)

    loader = PluginLoader(
        load_entrypoints=False,
        load_builtins=False,
        module_importer=_importer,
        iter_modules_fn=lambda _path, _prefix: [],
    )

    loader._load_builtin_plugins()

    assert loader.available_device_plugins() == tuple()
    assert loader.available_pc_plugins() == tuple()


def test_load_builtin_plugins_registers_pkg_modules_from_injected_iter_modules() -> None:
    package = SimpleNamespace(__path__=["dummy"])

    def _iter_modules(_path, prefix):
        return [
            pkgutil.ModuleInfo(module_finder=None, name=f"{prefix}ignore_me", ispkg=False),
            pkgutil.ModuleInfo(module_finder=None, name=f"{prefix}test_device", ispkg=True)
            if prefix.startswith("dpost.device_plugins")
            else pkgutil.ModuleInfo(
                module_finder=None, name=f"{prefix}test_pc", ispkg=True
            ),
        ]

    loader = PluginLoader(
        load_entrypoints=False,
        load_builtins=False,
        module_importer=_mapping_importer(
            {
                "dpost.device_plugins": package,
                "dpost.pc_plugins": package,
            }
        ),
        iter_modules_fn=_iter_modules,
    )

    loader._load_builtin_plugins()

    assert "test_device" in loader.available_device_plugins()
    assert "test_pc" in loader.available_pc_plugins()


def test_lazy_load_builtin_returns_false_for_unknown_group_and_registered_module() -> None:
    loader = PluginLoader(load_entrypoints=False, load_builtins=False)

    assert loader._lazy_load_builtin("unknown.group", "name") is False

    loader._registered_modules.add("dpost.device_plugins.test_device.plugin")
    assert loader._lazy_load_builtin(DEVICE_ENTRYPOINT_GROUP, "test_device") is False


def test_load_device_can_use_lazy_entrypoint_alias_module() -> None:
    loader = PluginLoader(
        load_entrypoints=False,
        load_builtins=False,
        module_importer=_mapping_importer({"fake.alias_device": _build_alias_device_module()}),
        iter_entry_points_fn=lambda group: [
            SimpleNamespace(name="alias_device", value="fake.alias_device")
        ]
        if group == DEVICE_ENTRYPOINT_GROUP
        else [],
    )

    plugin = loader.load_device("alias_device")

    assert isinstance(plugin, TestDevicePlugin)


def test_load_pc_can_use_lazy_entrypoint_alias_module() -> None:
    loader = PluginLoader(
        load_entrypoints=False,
        load_builtins=False,
        module_importer=_mapping_importer({"fake.alias_pc": _build_alias_pc_module()}),
        iter_entry_points_fn=lambda group: [SimpleNamespace(name="alias_pc", value="fake.alias_pc")]
        if group == PC_ENTRYPOINT_GROUP
        else [],
    )

    plugin = loader.load_pc("alias_pc")

    assert isinstance(plugin, TestPCPlugin)


def test_load_pc_triggers_builtin_fallback_when_lazy_discovery_yields_nothing() -> None:
    package = SimpleNamespace(__path__=["dummy"])
    loader = PluginLoader(
        load_entrypoints=False,
        load_builtins=False,
        module_importer=_mapping_importer(
            {
                "dpost.device_plugins": package,
                "dpost.pc_plugins": package,
            }
        ),
        iter_modules_fn=lambda _path, *, prefix: [],
        iter_entry_points_fn=lambda _group: [],
    )

    with pytest.raises(RuntimeError, match="No PC plugin named 'missing_pc'"):
        loader.load_pc("missing_pc")


def test_register_module_handles_already_registered_and_duplicate_or_invalid_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "dpost.device_plugins.test_device.plugin"
    module = importlib.import_module(module_name)

    loader = PluginLoader(load_entrypoints=False, load_builtins=False)
    loader._pm.register(module, name="manual-plugin")
    loader._register_module(
        module_name=module_name,
        registration_name="manual",
        log_context="manual",
    )
    assert module_name in loader._registered_modules

    duplicate_loader = PluginLoader(load_entrypoints=False, load_builtins=False)

    def _raise_duplicate(*_args, **_kwargs):
        raise ValueError("duplicate")

    monkeypatch.setattr(duplicate_loader._pm, "register", _raise_duplicate)
    duplicate_loader._register_module(
        module_name=module_name,
        registration_name="dup",
        log_context="dup",
    )
    assert module_name not in duplicate_loader._registered_modules

    validation_loader = PluginLoader(load_entrypoints=False, load_builtins=False)

    def _raise_validation(*_args, **_kwargs):
        raise pluggy.PluginValidationError("plugin", "invalid")

    monkeypatch.setattr(validation_loader._pm, "register", _raise_validation)
    validation_loader._register_module(
        module_name=module_name,
        registration_name="invalid",
        log_context="invalid",
    )
    assert module_name not in validation_loader._registered_modules


def test_register_module_returns_early_when_name_already_registered() -> None:
    calls: list[str] = []

    def _tracking_importer(module_name: str) -> object:
        calls.append(module_name)
        return importlib.import_module(module_name)

    loader = PluginLoader(
        load_entrypoints=False,
        load_builtins=False,
        module_importer=_tracking_importer,
    )
    module_name = "dpost.device_plugins.test_device.plugin"
    loader._registered_modules.add(module_name)

    loader._register_module(
        module_name=module_name,
        registration_name="already",
        log_context="already",
    )

    assert calls == []


def test_iter_entry_points_supports_pre310_mapping_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(plugin_system.sys, "version_info", (3, 9, 0))
    monkeypatch.setattr(
        plugin_system,
        "entry_points",
        lambda: {"example.group": ["a", "b"]},
    )

    resolved = list(plugin_system._iter_entry_points("example.group"))

    assert resolved == ["a", "b"]
