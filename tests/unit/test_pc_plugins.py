import pytest
from ipat_watchdog.loader import load_pc_plugin
from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.core.config.pc_settings import PCSettings

def test_load_test_pc_plugin():
    """Test loading the test PC plugin."""
    try:
        plugin = load_pc_plugin("test_pc")
    except RuntimeError as exc:
        pytest.skip(f"PC plugin 'test_pc' not available: {exc}")
        return
    assert isinstance(plugin, PCPlugin)

    settings = plugin.get_settings()
    assert isinstance(settings, PCSettings)

    # Verify test PC specific settings
    assert str(settings.WATCH_DIR).endswith("Upload")
    assert str(settings.DEST_DIR).endswith("Data")
    assert settings.PC_NAME == "TEST_PC"
    assert settings.PC_LOCATION == "Test Lab"

def test_load_real_pc_plugin():
    """Test loading a real PC plugin."""
    try:
        plugin = load_pc_plugin("tischrem_blb")
    except RuntimeError as exc:
        pytest.skip(f"PC plugin 'tischrem_blb' not available: {exc}")
        return
    assert isinstance(plugin, PCPlugin)

    settings = plugin.get_settings()
    assert isinstance(settings, PCSettings)

def test_pc_plugin_not_found():
    """Test error handling for non-existent PC plugin."""
    with pytest.raises(RuntimeError, match="No PC plugin named 'nonexistent'"):
        load_pc_plugin("nonexistent")
