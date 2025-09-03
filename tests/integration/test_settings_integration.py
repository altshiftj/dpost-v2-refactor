"""Integration test for the new settings system."""
import pytest
from pathlib import Path
from ipat_watchdog.core.config.settings_store import SettingsManager, SettingsStore
from ipat_watchdog.core.config.global_settings import GlobalSettings
from ipat_watchdog.core.config.device_settings_base import DeviceSettings


class TestDeviceA(DeviceSettings):
    """Test device A."""
    DEVICE_ID = "test_device_a"
    DEVICE_TYPE = "TYPE_A"
    ALLOWED_EXTENSIONS = {".tiff", ".tif"}
    SESSION_TIMEOUT = 120


class TestDeviceB(DeviceSettings):
    """Test device B."""
    DEVICE_ID = "test_device_b"
    DEVICE_TYPE = "TYPE_B"
    ALLOWED_EXTENSIONS = {".txt", ".csv"}
    SESSION_TIMEOUT = 180


def test_new_settings_system_integration():
    """Test the complete new settings system integration."""
    # Reset any existing settings
    SettingsStore.reset()
    
    # Create global settings
    global_settings = GlobalSettings()
    global_settings.WATCH_DIR = Path("./test_watch")
    global_settings.SESSION_TIMEOUT = 300
    
    # Create device settings
    device_a = TestDeviceA()
    device_b = TestDeviceB()
    
    # Create settings manager
    settings_manager = SettingsManager(global_settings, [device_a, device_b])
    SettingsStore.set_manager(settings_manager)
    
    # Test 1: Without device context, should get global settings
    settings = SettingsStore.get()
    assert settings is global_settings
    assert settings.WATCH_DIR == Path("./test_watch")
    assert settings.SESSION_TIMEOUT == 300
    
    # Test 2: With device context, should get composite settings
    settings_manager.set_current_device(device_a)
    composite = SettingsStore.get()
    assert composite is not global_settings
    assert composite.WATCH_DIR == Path("./test_watch")  # From global
    assert composite.SESSION_TIMEOUT == 120  # From device A
    assert composite.DEVICE_ID == "test_device_a"  # From device A
    
    # Test 3: Different device context
    settings_manager.set_current_device(device_b)
    composite = SettingsStore.get()
    assert composite.SESSION_TIMEOUT == 180  # From device B
    assert composite.DEVICE_ID == "test_device_b"  # From device B
    
    # Test 4: File selection
    selected_device = settings_manager.select_device_for_file("test.tiff")
    assert selected_device is device_a
    
    selected_device = settings_manager.select_device_for_file("test.txt")
    assert selected_device is device_b
    
    selected_device = settings_manager.select_device_for_file("test.unknown")
    assert selected_device is None
    
    # Test 5: Legacy API compatibility
    device = SettingsStore.find_processor_for_file("test.csv")
    assert device is device_b
    
    print("✅ All integration tests passed!")


if __name__ == "__main__":
    test_new_settings_system_integration()
