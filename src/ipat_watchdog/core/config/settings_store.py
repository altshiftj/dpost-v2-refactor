import threading
from typing import Optional, Dict, List
from .global_settings import PCSettings
from .device_settings_base import DeviceSettings
from .composite_settings import CompositeSettings


class SettingsManager:
    """Manages device selection and settings composition per processing context."""
    
    def __init__(self, global_settings: PCSettings, available_devices: List[DeviceSettings] = None, pc_settings: PCSettings = None):
        """
        Initialize settings manager.
        
        Args:
            global_settings: Application-wide settings (fallback)
            available_devices: List of device settings to register
            pc_settings: PC-specific settings from plugin (overrides global_settings if provided)
        """
        self._global = pc_settings if pc_settings is not None else global_settings
        self._devices = {}
        self._local = threading.local()
        
        # Register devices if provided
        if available_devices:
            for device in available_devices:
                self.register_device(device)
    
    def register_device(self, device_settings: DeviceSettings) -> None:
        """Register a device configuration."""
        device_id = device_settings.get_device_id()
        self._devices[device_id] = device_settings
    
    def select_device_for_file(self, filepath: str) -> Optional[DeviceSettings]:
        """Select appropriate device settings for a file."""
        for device in self._devices.values():
            if device.matches_file(filepath):
                return device
        return None
    
    def set_current_device(self, device_settings: Optional[DeviceSettings]) -> None:
        """Set device settings for current processing context."""
        self._local.device = device_settings
    
    def get_current_device(self) -> Optional[DeviceSettings]:
        """Get device settings for current processing context."""
        return getattr(self._local, 'device', None)
    
    def get_global_settings(self) -> PCSettings:
        """Get global settings."""
        return self._global
    
    def get_composite_settings(self) -> object:
        """Get composite settings for current processing context."""
        device = self.get_current_device()
        if device:
            return CompositeSettings(self._global, device)
        return self._global
    
    def find_compatible_devices(self, filepath: str) -> List[DeviceSettings]:
        """Find all devices that can process this file."""
        return [
            settings for settings in self._devices.values()
            if settings.matches_file(filepath)
        ]
    
    def get_all_devices(self) -> List[DeviceSettings]:
        """Get all registered device configurations."""
        return list(self._devices.values())


class SettingsStore:
    """Legacy settings store with device selection support."""
    _manager: Optional[SettingsManager] = None
    
    @classmethod
    def set_manager(cls, manager: SettingsManager) -> None:
        """Set the settings manager."""
        cls._manager = manager
    
    @classmethod
    def set(cls, settings: object) -> None:
        """
        Legacy method for backward compatibility.
        Creates a simple SettingsManager with global settings only.
        """
        if hasattr(settings, '__dict__'):
            # If it's a settings object, wrap it in a SettingsManager
            from .global_settings import PCSettings
            global_settings = PCSettings()
            # Copy attributes from the legacy settings object
            for attr, value in settings.__dict__.items():
                if hasattr(global_settings, attr):
                    setattr(global_settings, attr, value)
            cls._manager = SettingsManager(global_settings)
        else:
            # Direct assignment for tests or simple cases
            cls._manager = settings
    
    @classmethod
    def get(cls) -> object:
        """Get settings for current processing context."""
        if cls._manager is None:
            raise ValueError("Settings have not been initialized!")
        
        if hasattr(cls._manager, 'get_composite_settings'):
            return cls._manager.get_composite_settings()
        else:
            # Fallback for legacy usage
            return cls._manager
    
    @classmethod
    def get_manager(cls) -> SettingsManager:
        """Get the settings manager."""
        if cls._manager is None:
            raise ValueError("Settings manager has not been initialized!")
        return cls._manager
    
    @classmethod
    def find_processor_for_file(cls, filepath: str) -> Optional[DeviceSettings]:
        """
        Finds the appropriate device processor for a given file.
        Returns the first matching device settings or None if no match found.
        """
        if cls._manager is None:
            raise ValueError("Settings manager has not been initialized!")
        
        compatible_devices = cls._manager.find_compatible_devices(filepath)
        return compatible_devices[0] if compatible_devices else None
    
    @classmethod
    def reset(cls) -> None:
        """Reset the settings (useful in tests or controlled environments)."""
        cls._manager = None
    
    def __getattr__(self, name: str):
        """
        Delegate attribute access to the current composite settings.
        This maintains backward compatibility with the old SettingsStore API.
        """
        settings = self.__class__.get()
        return getattr(settings, name)
