# tests/unit/test_test_plugins_integration.py
"""
Tests for integration between test device and test PC plugins.
"""
import pytest
from pathlib import Path

from ipat_watchdog.device_plugins.test_device.plugin import TestDevicePlugin
from ipat_watchdog.device_plugins.test_device.settings import TestDeviceSettings
from ipat_watchdog.pc_plugins.test_pc.plugin import TestPCPlugin
from ipat_watchdog.pc_plugins.test_pc.settings import TestPCSettings
from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager


def test_test_plugins_compatible_ids():
    """Test that test device and PC plugins have compatible IDs."""
    device_plugin = TestDevicePlugin()
    device_settings = device_plugin.get_settings()
    
    pc_plugin = TestPCPlugin()
    pc_settings = pc_plugin.get_settings()
    
    # PC should map to the device
    assert device_settings.get_device_id() in pc_settings.DEVICE_MAPPING
    assert device_settings.get_device_id() in pc_settings.get_active_device_plugins()


def test_test_plugins_settings_manager_integration(tmp_path):
    """Test that both test plugins work with SettingsManager."""
    # Create path overrides
    override_paths = {
        'APP_DIR': tmp_path / "app",
        'WATCH_DIR': tmp_path / "upload",
        'DEST_DIR': tmp_path / "data",
        'RENAME_DIR': tmp_path / "data" / "rename",
        'EXCEPTIONS_DIR': tmp_path / "data" / "exceptions",
        'DAILY_RECORDS_JSON': tmp_path / "records.json",
        'LOG_FILE': tmp_path / "test.log"
    }
    
    # Create test device settings
    device_settings = TestDeviceSettings()
    for key, value in override_paths.items():
        setattr(device_settings, key, value)
    
    # Create test PC plugin
    pc_plugin = TestPCPlugin(override_paths=override_paths)
    pc_settings = pc_plugin.get_settings()
    
    # Create SettingsManager
    settings_manager = SettingsManager(
        available_devices=[device_settings],
        pc_settings=pc_settings
    )
    
    # Test integration
    assert settings_manager.get_global_settings().PC_NAME == "TEST_PC"
    assert len(settings_manager.get_all_devices()) == 1
    assert settings_manager.get_all_devices()[0].DEVICE_ID == "test_device"
    assert settings_manager.get_all_devices()[0].DEVICE_ABBR == "TEST"


def test_test_plugins_file_processing_paths(tmp_path):
    """Test that both plugins use consistent paths for file processing."""
    override_paths = {
        'WATCH_DIR': tmp_path / "upload",
        'DEST_DIR': tmp_path / "data"
    }
    
    # Create test device settings
    device_settings = TestDeviceSettings()
    for key, value in override_paths.items():
        setattr(device_settings, key, value)
    
    # Create test PC settings  
    pc_plugin = TestPCPlugin(override_paths=override_paths)
    pc_settings = pc_plugin.get_settings()
    
    # Both should use the same paths
    assert device_settings.WATCH_DIR == pc_settings.WATCH_DIR
    assert device_settings.DEST_DIR == pc_settings.DEST_DIR


def test_test_plugins_device_abbr_integration():
    """Test that device ABBR is correctly used in file processing."""
    device_settings = TestDeviceSettings()
    pc_plugin = TestPCPlugin()
    
    # Device should provide ABBR for folder structure
    assert hasattr(device_settings, 'DEVICE_ABBR')
    assert device_settings.DEVICE_ABBR == "TEST"
    
    # PC should map to the test device
    pc_settings = pc_plugin.get_settings()
    assert "test_device" in pc_settings.DEVICE_MAPPING
