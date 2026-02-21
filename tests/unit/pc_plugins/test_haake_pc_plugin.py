from __future__ import annotations

from dpost.pc_plugins.haake_blb.plugin import PCHaakePlugin, register_pc_plugins
from dpost.pc_plugins.haake_blb.settings import build_config
from dpost.plugins.system import PCPluginRegistry


def test_haake_pc_config_defaults():
    config = build_config()

    assert config.identifier == "haake_blb"
    assert config.active_device_plugins == ("extr_haake",)


def test_haake_pc_plugin_registration():
    registry = PCPluginRegistry()

    register_pc_plugins(registry)

    assert "haake_blb" in registry.names()

    plugin = registry.create("haake_blb")
    assert isinstance(plugin, PCHaakePlugin)
    assert plugin.get_config().identifier == "haake_blb"
