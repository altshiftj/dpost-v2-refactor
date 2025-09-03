from typing import Optional, Dict, List
from .global_settings import GlobalSettings
from .device_settings_base import DeviceSettings

class SettingsStore:
    _settings: Optional[object] = None

    @classmethod
    def set(cls, settings: object) -> None:
        """
        Sets the global settings object. Should be called once at application startup.
        """
        cls._settings = settings

    @classmethod
    def get(cls) -> object:
        """
        Retrieves the global settings object.
        Raises an error if it hasn't been initialized.
        """
        if cls._settings is None:
            raise ValueError("Settings have not been initialized!")
        return cls._settings

    @classmethod
    def reset(cls) -> None:
        """
        Resets the settings (useful in tests or controlled environments).
        """
        cls._settings = None


class SettingsManager:
    """Manages global and device-specific settings."""
    def __init__(self, global_settings: Optional[GlobalSettings] = None):
        self.global_settings = global_settings or GlobalSettings()
        self.device_settings: Dict[str, DeviceSettings] = {}

    def register_device(self, settings: DeviceSettings) -> None:
        """Register a device configuration."""
        device_id = settings.get_device_id()
        self.device_settings[device_id] = settings

    def get_device_settings(self, device_id: str) -> Optional[DeviceSettings]:
        """Get settings for specific device."""
        return self.device_settings.get(device_id)

    def find_compatible_devices(self, filepath: str) -> List[DeviceSettings]:
        """Find all devices that can process this file."""
        return [
            settings for settings in self.device_settings.values()
            if settings.matches_file(filepath)
        ]

    def get_all_devices(self) -> List[DeviceSettings]:
        """Get all registered device configurations."""
        return list(self.device_settings.values())
