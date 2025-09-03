"""Tests for DeviceSettings base class."""
import pytest
from pathlib import Path
import tempfile
import os
from ipat_watchdog.core.config.device_settings_base import DeviceSettings


class TestDeviceSettings(DeviceSettings):
    """Test implementation of DeviceSettings."""
    DEVICE_ID = "test_device"
    DEVICE_TYPE = "TEST"
    ALLOWED_EXTENSIONS = {".tiff", ".txt"}
    ALLOWED_FOLDER_CONTENTS = {".elid", ".odt"}


class TestDeviceSettingsMatching:
    """Test device settings file matching functionality."""

    def setup_method(self):
        """Set up test device settings."""
        self.device = TestDeviceSettings()

    def test_matches_file_with_allowed_extension(self):
        """Test file matching with allowed extension."""
        assert self.device.matches_file("test.tiff")
        assert self.device.matches_file("test.txt")
        assert self.device.matches_file("TEST.TIFF")  # Case insensitive

    def test_matches_file_with_disallowed_extension(self):
        """Test file matching with disallowed extension."""
        assert not self.device.matches_file("test.jpg")
        assert not self.device.matches_file("test.pdf")

    def test_matches_directory_with_allowed_contents(self):
        """Test directory matching with allowed contents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with allowed extensions
            (Path(temp_dir) / "file1.elid").touch()
            (Path(temp_dir) / "file2.odt").touch()
            
            assert self.device.matches_file(temp_dir)

    def test_matches_directory_with_disallowed_contents(self):
        """Test directory matching with disallowed contents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with disallowed extensions
            (Path(temp_dir) / "file1.jpg").touch()
            (Path(temp_dir) / "file2.pdf").touch()
            
            assert not self.device.matches_file(temp_dir)

    def test_matches_directory_with_mixed_contents(self):
        """Test directory matching with mixed contents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with both allowed and disallowed extensions
            (Path(temp_dir) / "file1.elid").touch()
            (Path(temp_dir) / "file2.jpg").touch()
            
            # Should match because it contains at least one allowed file
            assert self.device.matches_file(temp_dir)

    def test_get_device_id(self):
        """Test device ID retrieval."""
        assert TestDeviceSettings.get_device_id() == "test_device"
