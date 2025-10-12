"""Utility helpers that resolve registered device and PC plugins."""

from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.plugin_system import get_plugin_loader


def load_device_plugin(device_name: str) -> DevicePlugin:
    """Instantiate a device plugin via the shared plugin loader."""
    loader = get_plugin_loader()
    return loader.load_device(device_name)


def load_pc_plugin(pc_name: str) -> PCPlugin:
    """Instantiate a PC plugin via the shared plugin loader."""
    loader = get_plugin_loader()
    return loader.load_pc(pc_name)


def get_devices_for_pc(pc_name: str) -> list[str]:
    """Return the list of device plugin identifiers enabled for the PC."""
    pc_plugin = load_pc_plugin(pc_name)
    return list(pc_plugin.get_config().active_device_plugins)
