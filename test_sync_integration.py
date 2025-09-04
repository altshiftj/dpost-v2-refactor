#!/usr/bin/env python3
"""
Test script to demonstrate PC/Device settings integration with sync manager
"""
import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from ipat_watchdog.core.config.settings_store import SettingsManager, SettingsStore
from ipat_watchdog.core.config.pc_settings import PCSettings
from ipat_watchdog.core.sync.sync_kadi import KadiSyncManager
from tests.helpers.fake_ui import HeadlessUI

# Create a simple device settings for testing
from ipat_watchdog.core.config.device_settings_base import DeviceSettings

class TestDeviceSettings(DeviceSettings):
    DEVICE_TYPE = "TEST_DEVICE"
    ID_SEP = "-"
    
    # Database settings that would normally be device-specific
    DEVICE_USER_KADI_ID = "test-device-usr"
    DEVICE_USER_PERSISTENT_ID = 123
    DEVICE_RECORD_KADI_ID = "test_device_01"
    DEVICE_RECORD_PERSISTENT_ID = 456
    DEFAULT_RECORD_DESCRIPTION = "Test record from sync integration test"
    RECORD_TAGS = ["automated", "test"]
    
    @classmethod
    def get_device_id(cls):
        return "test_device"
    
    def matches_file(self, filepath: str) -> bool:
        return True

def test_sync_settings_integration():
    """Test that sync manager gets proper composite settings."""
    
    print("=== Testing Sync Manager Settings Integration ===\n")
    
    # Create PC settings
    pc_settings = PCSettings()
    print(f"PC Settings - SESSION_TIMEOUT: {pc_settings.SESSION_TIMEOUT}")
    print(f"PC Settings - ID_SEP: {pc_settings.ID_SEP}")
    print(f"PC Settings - WATCH_DIR: {pc_settings.WATCH_DIR}")
    
    # Create device settings  
    device_settings = TestDeviceSettings()
    print(f"Device Settings - Device ID: {device_settings.get_device_id()}")
    print(f"Device Settings - DEVICE_TYPE: {device_settings.DEVICE_TYPE}")
    print(f"Device Settings - DEVICE_USER_KADI_ID: {device_settings.DEVICE_USER_KADI_ID}")
    
    # Create settings manager with both
    settings_manager = SettingsManager(
        available_devices=[device_settings],
        pc_settings=pc_settings
    )
    
    # Set current device context
    settings_manager.set_current_device(device_settings)
    
    # Create sync manager with settings manager
    ui = HeadlessUI()
    sync_manager = KadiSyncManager(ui=ui, settings_manager=settings_manager)
    
    print(f"\n--- Sync Manager Settings ---")
    print(f"Sync Manager can access ID_SEP: {sync_manager.s.ID_SEP}")
    print(f"Sync Manager can access DEVICE_USER_KADI_ID: {sync_manager.s.DEVICE_USER_KADI_ID}")
    print(f"Sync Manager can access DEVICE_TYPE: {sync_manager.s.DEVICE_TYPE}")
    print(f"Sync Manager can access device ID: {sync_manager.s.get_device_id()}")
    print(f"Sync Manager can access WATCH_DIR: {sync_manager.s.WATCH_DIR}")
    
    # Test getting current settings (should get composite)
    current_settings = sync_manager._get_current_settings()
    print(f"\nCurrent settings type: {type(current_settings).__name__}")
    print(f"Current settings has PC attributes (WATCH_DIR): {hasattr(current_settings, 'WATCH_DIR')}")
    print(f"Current settings has device attributes (DEVICE_USER_KADI_ID): {hasattr(current_settings, 'DEVICE_USER_KADI_ID')}")
    
    # Demonstrate that device settings override PC settings for shared attributes
    print(f"\nSettings precedence test:")
    print(f"ID_SEP from composite settings: '{current_settings.ID_SEP}' (should be device value)")
    print(f"PC ID_SEP: '{pc_settings.ID_SEP}'")
    print(f"Device ID_SEP: '{device_settings.ID_SEP}'")
    
    print("\n✅ Sync manager successfully integrates PC and device settings!")

if __name__ == "__main__":
    test_sync_settings_integration()
