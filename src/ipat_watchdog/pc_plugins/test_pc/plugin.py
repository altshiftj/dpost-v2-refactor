# ipat_watchdog/pc_plugins/test_pc/plugin.py
"""
Test PC Plugin - Simple PC plugin for testing purposes.
"""
from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.core.config.pc_settings import PCSettings
from .settings import TestPCSettings


class TestPCPlugin(PCPlugin):
    """
    Test PC plugin for isolated testing.
    Provides minimal PC functionality without external dependencies.
    """
    
    def __init__(self, override_paths=None):
        """Initialize test PC plugin with optional path overrides."""
        self._settings = TestPCSettings(override_paths=override_paths)
    
    def get_settings(self) -> PCSettings:
        """Get test PC settings instance."""
        return self._settings
