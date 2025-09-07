# tests/unit/test_test_pc_plugin.py
"""
Tests for the test PC plugin to ensure it provides proper isolation.
"""
import pytest
from pathlib import Path

from ipat_watchdog.pc_plugins.test_pc.plugin import TestPCPlugin
from ipat_watchdog.pc_plugins.test_pc.settings import TestPCSettings


def test_test_pc_plugin_basic_functionality():
    """Test that test PC plugin creates properly configured settings."""
    plugin = TestPCPlugin()
    settings = plugin.get_settings()
    
    assert isinstance(settings, TestPCSettings)
    assert settings.PC_NAME == "TEST_PC"
    assert settings.PC_LOCATION == "Test Lab"
    assert "test_device" in settings.DEVICE_MAPPING


def test_test_pc_plugin_path_overrides(tmp_path):
    """Test that test PC plugin accepts path overrides for testing."""
    override_paths = {
        'WATCH_DIR': tmp_path / "test_upload",
        'DEST_DIR': tmp_path / "test_data",
        'RENAME_DIR': tmp_path / "test_data" / "rename",
        'EXCEPTIONS_DIR': tmp_path / "test_data" / "exceptions",
    }
    
    plugin = TestPCPlugin(override_paths=override_paths)
    settings = plugin.get_settings()
    
    assert settings.WATCH_DIR == override_paths['WATCH_DIR']
    assert settings.DEST_DIR == override_paths['DEST_DIR']
    assert settings.RENAME_DIR == override_paths['RENAME_DIR']
    assert settings.EXCEPTIONS_DIR == override_paths['EXCEPTIONS_DIR']


def test_test_pc_settings_device_mapping():
    """Test that test PC settings has correct device mapping."""
    settings = TestPCSettings()
    
    assert settings.get_pc_id() == "test_pc"
    assert settings.get_active_device_plugins() == ["test_device"]
    assert settings.validate_configuration() is True


def test_test_pc_settings_paths():
    """Test that test PC settings has expected default paths."""
    settings = TestPCSettings()
    
    # Should have default paths
    assert hasattr(settings, 'WATCH_DIR')
    assert hasattr(settings, 'DEST_DIR')
    assert hasattr(settings, 'RENAME_DIR')
    assert hasattr(settings, 'EXCEPTIONS_DIR')
    
    # Paths should be Path objects
    assert isinstance(settings.WATCH_DIR, Path)
    assert isinstance(settings.DEST_DIR, Path)


def test_test_pc_plugin_integration_with_device():
    """Test that test PC plugin works well with test device plugin."""
    plugin = TestPCPlugin()
    settings = plugin.get_settings()
    
    # Should map to test device
    device_mapping = settings.DEVICE_MAPPING
    assert "test_device" in device_mapping
    assert device_mapping["test_device"] == "test_device"
    
    # Should have test device in active plugins
    active_devices = settings.get_active_device_plugins()
    assert "test_device" in active_devices
