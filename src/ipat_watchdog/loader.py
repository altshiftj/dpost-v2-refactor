# src/ipat_watchdog/loader.py
from importlib.metadata import entry_points

def load_device_plugin(device_name: str):
    """
    Return an instance of the plugin that registered itself under
    the given device_name in the 'ipat_watchdog.plugins' group.
    """
    eps = entry_points(group="ipat_watchdog.plugins")
    try:
        plugin_cls = eps[device_name].load()
    except KeyError:
        raise RuntimeError(f"No plugin called {device_name!r} is installed")

    return plugin_cls()     # instantiate
