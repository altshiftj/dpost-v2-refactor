"""Plugin package surface for dpost device and PC extensions."""

from dpost.plugins.contracts import DevicePlugin, PCPlugin
from dpost.plugins.loading import get_devices_for_pc, load_device_plugin, load_pc_plugin
from dpost.plugins.reference import REFERENCE_PLUGIN_PROFILE, PluginProfile
from dpost.plugins.system import get_plugin_loader

__all__ = [
    "DevicePlugin",
    "PCPlugin",
    "PluginProfile",
    "REFERENCE_PLUGIN_PROFILE",
    "get_devices_for_pc",
    "get_plugin_loader",
    "load_device_plugin",
    "load_pc_plugin",
]
