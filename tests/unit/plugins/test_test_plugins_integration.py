"""Tests for integration between test device and test PC plugins."""
from pathlib import Path

from ipat_watchdog.device_plugins.test_device.plugin import TestDevicePlugin
from ipat_watchdog.device_plugins.test_device.settings import build_config as build_device_config
from ipat_watchdog.pc_plugins.test_pc.plugin import TestPCPlugin
from ipat_watchdog.pc_plugins.test_pc.settings import build_config as build_pc_config


def test_test_device_plugin_config():
    plugin = TestDevicePlugin()
    config = plugin.get_config()

    assert config.identifier == "test_device"
    assert ".tif" in config.files.allowed_extensions
    assert config.metadata.device_abbr == "TEST"


def test_test_pc_plugin_config_includes_test_device():
    plugin = TestPCPlugin()
    config = plugin.get_config()
    assert "test_device" in config.active_device_plugins


def test_path_overrides_apply_to_configs(tmp_path):
    overrides = {
        "app_dir": tmp_path / "app",
        "watch_dir": tmp_path / "upload",
        "dest_dir": tmp_path / "data",
        "rename_dir": tmp_path / "data" / "rename",
        "exceptions_dir": tmp_path / "data" / "exceptions",
        "daily_records_json": tmp_path / "records.json",
    }

    pc_config = build_pc_config(override_paths=overrides)
    device_config = build_device_config()

    assert pc_config.paths.watch_dir == overrides["watch_dir"]
    assert pc_config.paths.dest_dir == overrides["dest_dir"]
    assert device_config.identifier == "test_device"


def test_device_and_pc_configs_share_separator_settings():
    device_config = build_device_config()
    pc_config = build_pc_config()
    assert pc_config.naming.id_separator == "-"
    assert device_config.metadata.device_abbr == "TEST"
