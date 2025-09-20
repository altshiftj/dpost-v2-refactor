import pytest

from ipat_watchdog.loader import load_pc_plugin
from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.core.config import PCConfig


def test_load_test_pc_plugin():
    """Test loading the test PC plugin."""
    try:
        plugin = load_pc_plugin("test_pc")
    except RuntimeError as exc:
        pytest.skip(f"PC plugin 'test_pc' not available: {exc}")
        return
    assert isinstance(plugin, PCPlugin)

    config = plugin.get_config()
    assert isinstance(config, PCConfig)
    assert config.identifier == "test_pc"
    assert "test_device" in config.active_device_plugins
    assert str(config.paths.watch_dir).endswith("Upload")
    assert str(config.paths.dest_dir).endswith("Data")


def test_load_real_pc_plugin():
    """Test loading a real PC plugin."""
    try:
        plugin = load_pc_plugin("tischrem_blb")
    except RuntimeError as exc:
        pytest.skip(f"PC plugin 'tischrem_blb' not available: {exc}")
        return
    assert isinstance(plugin, PCPlugin)

    config = plugin.get_config()
    assert isinstance(config, PCConfig)


def test_pc_plugin_not_found():
    """Test error handling for non-existent PC plugin."""
    with pytest.raises(RuntimeError, match="No PC plugin named 'nonexistent'"):
        load_pc_plugin("nonexistent")
