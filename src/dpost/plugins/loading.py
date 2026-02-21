"""Plugin loading helpers resolved through canonical dpost plugin boundaries."""

from dpost.plugins.contracts import DevicePlugin, PCPlugin
from dpost.plugins.system import get_plugin_loader


def load_device_plugin(device_name: str) -> DevicePlugin:
    """Instantiate a device plugin via the shared dpost plugin loader."""
    loader = get_plugin_loader()
    return loader.load_device(device_name)


def load_pc_plugin(pc_name: str) -> PCPlugin:
    """Instantiate a PC plugin via the shared dpost plugin loader."""
    loader = get_plugin_loader()
    return loader.load_pc(pc_name)


def get_devices_for_pc(pc_name: str) -> list[str]:
    """Return the list of active device plugin identifiers for a PC plugin."""
    pc_plugin = load_pc_plugin(pc_name)
    return list(pc_plugin.get_config().active_device_plugins)
