"""
Composite settings that combine global and device-specific settings.
"""
from typing import Any
from .global_settings import PCSettings
from .device_settings_base import DeviceSettings


class CompositeSettings:
    """
    Composite settings combining global and device-specific settings.
    
    Device-specific settings take precedence over global settings.
    This allows per-file processing with appropriate device context
    while maintaining global application settings.
    """
    
    def __init__(self, global_settings: PCSettings, device_settings: DeviceSettings):
        """
        Initialize composite settings.
        
        Args:
            global_settings: Application-wide settings
            device_settings: Device-specific settings
        """
        self._global = global_settings
        self._device = device_settings
    
    def __getattr__(self, name: str) -> Any:
        """
        Get attribute value, preferring device settings over global settings.
        
        Args:
            name: Attribute name to retrieve
            
        Returns:
            Attribute value from device settings if available, otherwise from global settings
            
        Raises:
            AttributeError: If attribute is not found in either settings object
        """
        # First check device settings
        if hasattr(self._device, name):
            return getattr(self._device, name)
        
        # Fall back to global settings
        if hasattr(self._global, name):
            return getattr(self._global, name)
        
        # Not found in either
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    def get_global_settings(self) -> PCSettings:
        """Get the underlying global settings object."""
        return self._global
    
    def get_device_settings(self) -> DeviceSettings:
        """Get the underlying device settings object."""
        return self._device
    
    @property
    def device_id(self) -> str:
        """Get the device ID from device settings."""
        return self._device.get_device_id()
