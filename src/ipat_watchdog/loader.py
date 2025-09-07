# src/ipat_watchdog/loader.py
from importlib.metadata import entry_points
from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin

def load_device_plugin(device_name: str) -> DevicePlugin:
    """
    Resolve a plugin published via the 'ipat_watchdog.plugins' entry‑point group.
    `device_name` must match the *key* in pyproject.toml (e.g. 'sem_phenomxl2').
    """
    eps = entry_points(group="ipat_watchdog.device_plugins")
    try:
        cls = eps[device_name].load()
        return cls()                      # instantiate
    except KeyError as exc:
        raise RuntimeError(
            f"No plugin named {device_name!r} installed. "
            "Run `pip install ipat-watchdog[{device_name_lower}]`."
            "or check casing of the device name (only lowercase names, please :)."
        ) from exc


def load_pc_plugin(pc_name: str) -> PCPlugin:
    """
    Resolve a PC plugin published via the 'ipat_watchdog.pc_plugins' entry‑point group.
    `pc_name` must match the *key* in pyproject.toml (e.g. 'tischrem_blb').
    """
    eps = entry_points(group="ipat_watchdog.pc_plugins")
    try:
        cls = eps[pc_name].load()
        return cls()                      # instantiate
    except KeyError as exc:
        raise RuntimeError(
            f"No PC plugin named {pc_name!r} installed. "
            "Run `pip install ipat-watchdog[{pc_name}]`."
            "or check casing of the PC name (only lowercase names, please :)."
        ) from exc


def get_devices_for_pc(pc_name: str) -> list[str]:
    """
    Get the list of device names for a given PC name from the PC plugin settings.
    Returns a list of device plugin names that should be loaded for this PC.
    """
    pc_plugin = load_pc_plugin(pc_name)
    return pc_plugin.get_settings().get_active_device_plugins()
