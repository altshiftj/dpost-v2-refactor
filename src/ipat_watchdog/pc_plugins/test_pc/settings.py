# ipat_watchdog/pc_plugins/test_pc/settings.py
"""
Test PC Settings - Simple PC configuration for testing purposes.
"""
from pathlib import Path
from typing import Optional

from ipat_watchdog.core.config.pc_settings import PCSettings


class TestPCSettings(PCSettings):
    """
    Test PC settings for isolated testing.
    Provides minimal PC configuration without external dependencies.
    """
    
    def __init__(self, override_paths: Optional[dict] = None):
        """
        Initialize test PC settings.
        
        Args:
            override_paths: Optional dictionary to override default paths for testing
        """
        super().__init__()
        
        # Apply path overrides if provided (useful for tests)
        if override_paths:
            for key, value in override_paths.items():
                if hasattr(self, key):
                    setattr(self, key, value)
    
    # PC Identity
    PC_NAME = "TEST_PC"
    PC_LOCATION = "Test Lab"
    
    # Device mapping - maps to test device
    DEVICE_MAPPING = {
        "test_device": "test_device"
    }
    
    # File paths (can be overridden for testing)
    WATCH_DIR = Path.home() / "Desktop" / "Upload"
    DEST_DIR = Path.home() / "Desktop" / "Data"
    RENAME_DIR = Path.home() / "Desktop" / "Data" / "00_To_Rename"
    EXCEPTIONS_DIR = Path.home() / "Desktop" / "Data" / "01_Exceptions"
    
    # Test-specific settings
    DAILY_RECORDS_JSON = DEST_DIR / "test_records.json"
    
    @classmethod
    def get_pc_id(cls) -> str:
        """Get unique PC identifier for testing."""
        return "test_pc"
    
    def get_active_device_plugins(self) -> list[str]:
        """Return list of active device plugins for this PC."""
        return ["test_device"]
    
    def validate_configuration(self) -> bool:
        """Validate PC configuration - always returns True for testing."""
        return True
