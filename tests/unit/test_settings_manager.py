"""Tests for the new SettingsManager and SettingsStore."""
import pytest
import threading
import time
from pathlib import Path
from ipat_watchdog.core.config.settings_store import SettingsManager, SettingsStore
from ipat_watchdog.core.config.device_settings_base import DeviceSettings
from ipat_watchdog.core.config.global_settings import PCSettings


class TestDeviceA(DeviceSettings):
    """Mock device A for testing."""
    DEVICE_ID = "device_a"
    DEVICE_TYPE = "TYPE_A"
    ALLOWED_EXTENSIONS = {".tiff", ".tif"}
    SESSION_TIMEOUT = 120


class TestDeviceB(DeviceSettings):
    """Mock device B for testing.""" 
    DEVICE_ID = "device_b"
    DEVICE_TYPE = "TYPE_B"
    ALLOWED_EXTENSIONS = {".txt", ".csv"}
    SESSION_TIMEOUT = 180


class TestSettingsManager:
    """Test SettingsManager functionality."""

    def setup_method(self):
        """Set up test settings."""
        self.global_settings = PCSettings()
        self.device_a = TestDeviceA()
        self.device_b = TestDeviceB()
        self.manager = SettingsManager(
            self.global_settings, 
            [self.device_a, self.device_b]
        )

    def test_device_registration(self):
        """Test device registration."""
        assert len(self.manager.get_all_devices()) == 2
        devices = {d.get_device_id() for d in self.manager.get_all_devices()}
        assert devices == {"device_a", "device_b"}

    def test_device_selection_for_file(self):
        """Test device selection based on file type."""
        # Test file matching
        device_for_tiff = self.manager.select_device_for_file("test.tiff")
        assert device_for_tiff is not None
        assert device_for_tiff.get_device_id() == "device_a"
        
        device_for_txt = self.manager.select_device_for_file("test.txt")
        assert device_for_txt is not None
        assert device_for_txt.get_device_id() == "device_b"
        
        # Test no match
        device_for_unknown = self.manager.select_device_for_file("test.xyz")
        assert device_for_unknown is None

    def test_thread_local_device_setting(self):
        """Test that device settings are thread-local."""
        # Initially no device set
        assert self.manager.get_current_device() is None
        
        # Set device A in main thread
        self.manager.set_current_device(self.device_a)
        assert self.manager.get_current_device() is self.device_a
        
        # Test thread isolation
        results = {}
        
        def thread_function(device, thread_id):
            self.manager.set_current_device(device)
            time.sleep(0.1)  # Small delay to ensure concurrency
            results[thread_id] = self.manager.get_current_device()
        
        # Start two threads with different devices
        thread1 = threading.Thread(target=thread_function, args=(self.device_a, "thread1"))
        thread2 = threading.Thread(target=thread_function, args=(self.device_b, "thread2"))
        
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()
        
        # Each thread should have its own device
        assert results["thread1"] is self.device_a
        assert results["thread2"] is self.device_b
        
        # Main thread should still have its original device
        assert self.manager.get_current_device() is self.device_a

    def test_composite_settings(self):
        """Test composite settings creation."""
        # Without device context, should return global settings
        settings = self.manager.get_composite_settings()
        assert settings is self.global_settings
        
        # With device context, should return composite
        self.manager.set_current_device(self.device_a)
        composite = self.manager.get_composite_settings()
        assert composite is not self.global_settings
        assert composite.get_device_settings() is self.device_a
        assert composite.get_global_settings() is self.global_settings


class TestSettingsStore:
    """Test SettingsStore backward compatibility."""

    def setup_method(self):
        """Set up test settings."""
        # Reset the store for each test
        SettingsStore.reset()
        
        self.global_settings = PCSettings()
        self.device_a = TestDeviceA()
        self.manager = SettingsManager(self.global_settings, [self.device_a])

    def teardown_method(self):
        """Clean up after each test."""
        SettingsStore.reset()

    def test_settings_store_with_manager(self):
        """Test SettingsStore with new manager."""
        SettingsStore.set_manager(self.manager)
        
        # Should return global settings when no device is set
        settings = SettingsStore.get()
        assert settings is self.global_settings
        
        # Should return composite when device is set
        self.manager.set_current_device(self.device_a)
        composite = SettingsStore.get()
        assert composite is not self.global_settings
        assert composite.SESSION_TIMEOUT == 120  # Device value

    def test_find_processor_for_file(self):
        """Test file processor finding functionality."""
        SettingsStore.set_manager(self.manager)
        
        # Should find device A for .tiff files
        device = SettingsStore.find_processor_for_file("test.tiff")
        assert device is not None
        assert device.get_device_id() == "device_a"
        
        # Should find nothing for unknown files
        device = SettingsStore.find_processor_for_file("test.unknown")
        assert device is None
