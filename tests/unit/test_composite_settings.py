"""Tests for CompositeSettings class."""
import pytest
from pathlib import Path
from ipat_watchdog.core.config.composite_settings import CompositeSettings


class MockGlobalSettings:
    """Mock global settings for testing."""
    WATCH_DIR = Path("./global_watch")
    SESSION_TIMEOUT = 300
    GLOBAL_ONLY_SETTING = "global_value"
    SHARED_SETTING = "global_shared"


class MockDeviceSettings:
    """Mock device settings for testing."""
    DEVICE_ID = "test_device"
    DEVICE_ONLY_SETTING = "device_value"
    SHARED_SETTING = "device_shared"  # Should override global


class TestCompositeSettings:
    """Test composite settings functionality."""

    def setup_method(self):
        """Set up test settings."""
        self.global_settings = MockGlobalSettings()
        self.device_settings = MockDeviceSettings()
        self.composite = CompositeSettings(self.global_settings, self.device_settings)

    def test_device_setting_overrides_global(self):
        """Test that device settings override global settings for same attribute."""
        assert self.composite.SHARED_SETTING == "device_shared"

    def test_device_only_settings_accessible(self):
        """Test that device-only settings are accessible."""
        assert self.composite.DEVICE_ONLY_SETTING == "device_value"
        assert self.composite.DEVICE_ID == "test_device"

    def test_global_only_settings_accessible(self):
        """Test that global-only settings are accessible."""
        assert self.composite.GLOBAL_ONLY_SETTING == "global_value"
        assert self.composite.WATCH_DIR == Path("./global_watch")

    def test_global_fallback_for_device_missing_attribute(self):
        """Test fallback to global when device doesn't have attribute."""
        assert self.composite.SESSION_TIMEOUT == 300  # From global

    def test_attribute_error_for_missing_attribute(self):
        """Test that AttributeError is raised for missing attributes."""
        with pytest.raises(AttributeError) as exc_info:
            _ = self.composite.NON_EXISTENT_SETTING
        
        assert "has no attribute 'NON_EXISTENT_SETTING'" in str(exc_info.value)

    def test_access_to_underlying_settings(self):
        """Test access to underlying settings objects."""
        assert self.composite.get_global_settings() is self.global_settings
        assert self.composite.get_device_settings() is self.device_settings
