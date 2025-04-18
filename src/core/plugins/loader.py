# core/plugins/loader.py
import importlib
from pathlib import Path
from types import ModuleType
from typing import Type

from src.core.plugins.device_plugin import DevicePlugin

def _camel_to_snake(name: str) -> str:
    return ''.join(f"_{c.lower()}" if c.isupper() else c for c in name).lstrip('_')

def load_device_plugin(device_folder: str) -> DevicePlugin:
    """
    Dynamically import `<device_folder>.plugin` and return its *only*
    `DevicePlugin` subclass.
    """
    module_path = f"src.devices.{device_folder}.plugin"
    module: ModuleType = importlib.import_module(module_path)

    # Find the first class that inherits from DevicePlugin
    for attr in vars(module).values():
        if isinstance(attr, type) and issubclass(attr, DevicePlugin) and attr is not DevicePlugin:
            return attr()  # instantiate

    raise ImportError(f"No DevicePlugin subclass found in {module_path!r}")


def discover_plugins() -> dict[str, Path]:
    """
    Optional: walk the `devices/` directory and list folders that contain
    a `plugin.py` – handy for CLI autocompletion or config UIs.
    """
    root = Path(__file__).resolve().parents[2] / "devices"
    return {p.name: p for p in root.iterdir() if (p / "plugin.py").is_file()}
