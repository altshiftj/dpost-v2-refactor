# ipat_watchdog/device_plugins/test_device/settings.py
from ipat_watchdog.core.config.device_settings_base import DeviceSettings
import re

class TestDeviceSettings(DeviceSettings):
    """
    Test device configuration for unit and integration tests.
    Provides a minimal, predictable setup for testing.
    """

    # Device identity
    DEVICE_ID = "test_device"

    # ──────────────────────────────────────────────────────────────────────────────
    # 📂 File Settings
    # ──────────────────────────────────────────────────────────────────────────────
    ALLOWED_EXTENSIONS = {".tif", ".txt"}
    ALLOWED_FOLDER_CONTENTS = set()

    # ──────────────────────────────────────────────────────────────────────────────
    # 📟 Device Identity
    # ──────────────────────────────────────────────────────────────────────────────
    
    DEVICE_USER_KADI_ID = "test-01-usr"
    DEVICE_USER_PERSISTENT_ID = 999
    DEVICE_RECORD_KADI_ID = "test_01"
    DEVICE_RECORD_PERSISTENT_ID = 999
    DEVICE_ABBR = "TEST"

    # ──────────────────────────────────────────────────────────────────────────────
    # 📝 Metadata Defaults
    # ──────────────────────────────────────────────────────────────────────────────
    RECORD_TAGS = [
        "Test Data",
        "Unit Testing",
    ]

    DEFAULT_RECORD_DESCRIPTION = r"""
    # Test Record Description
    *This is a test record created during automated testing*

    ## Overview
    **Device:** Test Device for Unit/Integration Testing
    **Data Types:** Test files (.tif, .txt)
    
    This record was created by the test suite and contains synthetic test data.
    """

    # ──────────────────────────────────────────────────────────────────────────────
    # 🕐 Timeouts
    # ──────────────────────────────────────────────────────────────────────────────
    SESSION_TIMEOUT = 300  # 5 minutes for tests

    # ──────────────────────────────────────────────────────────────────────────────
    # 📋 Processing Settings
    # ──────────────────────────────────────────────────────────────────────────────
    DEBOUNCE_TIME = 0.1  # Fast for tests

    @classmethod
    def get_device_id(cls) -> str:
        return "test_device"
    
    def matches_file(self, filepath: str) -> bool:
        """Check if this device can process the given file."""
        from pathlib import Path
        return Path(filepath).suffix.lower() in self.ALLOWED_EXTENSIONS
