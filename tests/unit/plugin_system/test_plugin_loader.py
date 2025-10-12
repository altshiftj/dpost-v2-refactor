from __future__ import annotations

import importlib

import pytest

from ipat_watchdog.device_plugins.test_device.plugin import TestDevicePlugin
from ipat_watchdog.pc_plugins.test_pc.plugin import TestPCPlugin
from ipat_watchdog.plugin_system import PluginLoader, hookimpl

pytestmark = pytest.mark.filterwarnings("ignore::pytest.PytestCollectionWarning")


def _make_loader() -> PluginLoader:
    """Create a loader without relying on distribution entry points."""
    loader = PluginLoader(load_entrypoints=False, load_builtins=False)
    return loader


def test_register_device_plugin_via_hook():
    loader = _make_loader()
    module = importlib.import_module("ipat_watchdog.device_plugins.test_device.plugin")
    loader.register_plugin(module, name="test-device-module")

    plugin = loader.load_device("test_device")
    assert isinstance(plugin, TestDevicePlugin)
    assert "test_device" in loader.available_device_plugins()


def test_register_pc_plugin_via_hook():
    loader = _make_loader()
    module = importlib.import_module("ipat_watchdog.pc_plugins.test_pc.plugin")
    loader.register_plugin(module, name="test-pc-module")

    plugin = loader.load_pc("test_pc")
    assert isinstance(plugin, TestPCPlugin)
    assert "test_pc" in loader.available_pc_plugins()


def test_duplicate_device_registration_raises():
    loader = _make_loader()

    class DuplicatePlugin:
        @hookimpl
        def register_device_plugins(self, registry):
            registry.register("dup_device", TestDevicePlugin)
            registry.register("dup_device", TestDevicePlugin)

    with pytest.raises(ValueError, match="dup_device"):
        loader.register_plugin(DuplicatePlugin(), name="duplicate-device")
