#!/usr/bin/env python3
"""
Test script to demonstrate PC/Device settings integration with sync manager
"""
from pathlib import Path
import sys

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from ipat_watchdog.core.config.settings_store import SettingsManager, SettingsStore
from ipat_watchdog.core.config.pc_settings import PCSettings
from ipat_watchdog.core.sync.sync_kadi import KadiSyncManager
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from tests.helpers.fake_ui import HeadlessUI

# Create a simple device settings for testing
from ipat_watchdog.core.config.device_settings_base import DeviceSettings

class TestDeviceSettings(DeviceSettings):
    DEVICE_ABBR = "TEST_DEVICE"
    ID_SEP = "-"
    # Database settings that would normally be device-specific
    DEVICE_USER_KADI_ID = "test-device-usr"
    DEVICE_USER_PERSISTENT_ID = 123
    DEVICE_RECORD_KADI_ID = "test_device_01"
    DEVICE_RECORD_PERSISTENT_ID = 456
    DEFAULT_RECORD_DESCRIPTION = "Test record from sync integration test"
    RECORD_TAGS = ["automated", "test"]
    @classmethod
    def matches_file(self, filepath: str) -> bool:
        return True

def test_sync_settings_integration():
    """Test that sync manager gets proper composite settings."""
    # Create fake PC settings
    class FakePCSettings(PCSettings):
        APP_DIR = Path("/tmp/app")
        def get_active_device_plugins(self):
            return ["test_device"]

    pc_settings = FakePCSettings()
    device_settings = TestDeviceSettings()
    settings_manager = SettingsManager(available_devices=[device_settings], pc_settings=pc_settings)
    SettingsStore.set_manager(settings_manager)

    ui = HeadlessUI()
    sync_manager = KadiSyncManager(ui=ui, settings_manager=settings_manager)

    # Test record sync without device context
    print("4. Testing record sync...")
    from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
    from ipat_watchdog.core.session.session_manager import SessionManager
    
    session_manager = SessionManager(ui=ui, end_session_callback=lambda: None)
    file_process_manager = FileProcessManager(ui=ui, sync_manager=sync_manager, session_manager=session_manager)
    file_process_manager.sync_records_to_database()
    print("   ✓ Record sync completed")
    
    composite = settings_manager.get_composite_settings()
    print("Composite settings type:", type(composite).__name__)
    if hasattr(composite, 'device_id'):
        print("Composite settings device ID:", composite.device_id)
    print("Composite settings global APP_DIR:", composite.get_global_settings().APP_DIR if hasattr(composite, 'get_global_settings') else getattr(composite, 'APP_DIR', 'N/A'))
    if hasattr(composite, 'get_device_settings'):
        print("Composite settings device ABBR:", composite.get_device_settings().DEVICE_ABBR)
    print("Sync manager type:", type(sync_manager).__name__)

if __name__ == "__main__":
    print("Running test_sync_settings_integration...")
    test_sync_settings_integration()
