# src/ipat_watchdog/loader.py
from importlib.metadata import entry_points
from ipat_watchdog.device_plugins.device_plugin import DevicePlugin

def load_device_plugin(device_name: str) -> DevicePlugin:
    """
    Resolve a plugin published via the 'ipat_watchdog.plugins' entry‑point group.
    `device_name` must match the *key* in pyproject.toml (e.g. 'sem_tischrem_blb').
    """
    eps = entry_points(group="ipat_watchdog.plugins")
    try:
        cls = eps[device_name].load()
        return cls()                      # instantiate
    except KeyError as exc:
        raise RuntimeError(
            f"No plugin named {device_name!r} installed. "
            "Run `pip install ipat-watchdog[{device_name_lower}]`."
            "or check casing of the device name (only lowercase names, please :)."
        ) from exc
