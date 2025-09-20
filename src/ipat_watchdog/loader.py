"""Utility functions that resolve registered device and PC plugins."""

from importlib.metadata import entry_points

from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin


def load_device_plugin(device_name: str) -> DevicePlugin:
    """Resolve a device plugin published via the entry-point group."""
    eps = entry_points(group="ipat_watchdog.device_plugins")
    try:
        cls = eps[device_name].load()
        return cls()  # instantiate
    except KeyError as exc:
        raise RuntimeError(
            f"No device plugin named {device_name!r} installed. "
            "Run `pip install ipat-watchdog[{device_name}]` or check casing."
        ) from exc


def load_pc_plugin(pc_name: str) -> PCPlugin:
    """Resolve a PC plugin published via the entry-point group."""
    eps = entry_points(group="ipat_watchdog.pc_plugins")
    try:
        cls = eps[pc_name].load()
        return cls()  # instantiate
    except KeyError as exc:
        raise RuntimeError(
            f"No PC plugin named {pc_name!r} installed. "
            "Run `pip install ipat-watchdog[{pc_name}]` or check casing."
        ) from exc


def get_devices_for_pc(pc_name: str) -> list[str]:
    """Return the list of device plugin identifiers enabled for the PC."""
    pc_plugin = load_pc_plugin(pc_name)
    return list(pc_plugin.get_config().active_device_plugins)
