import pytest
from ipat_watchdog.loader import load_pc_plugin
from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.core.config.global_settings import PCSettings

def test_load_default_pc_plugin():
    """Test loading the default PC plugin."""
    plugin = load_pc_plugin("default_pc_blb")
    assert isinstance(plugin, PCPlugin)
    
    settings = plugin.get_settings()
    assert isinstance(settings, PCSettings)

def test_load_lab_workstation_plugin():
    """Test loading the lab workstation PC plugin."""
    plugin = load_pc_plugin("lab_workstation_blb")
    assert isinstance(plugin, PCPlugin)
    
    settings = plugin.get_settings()
    assert isinstance(settings, PCSettings)
    
    # Verify lab-specific overrides
    assert str(settings.WATCH_DIR) == "D:\\LabData\\Upload"
    assert str(settings.DEST_DIR) == "D:\\LabData\\Processed"
    assert settings.POLL_SECONDS == 0.5

def test_pc_plugin_not_found():
    """Test error handling for non-existent PC plugin."""
    with pytest.raises(RuntimeError, match="No PC plugin named 'nonexistent'"):
        load_pc_plugin("nonexistent")
