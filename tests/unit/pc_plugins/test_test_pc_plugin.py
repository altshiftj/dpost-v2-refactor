"""Tests for the test PC plugin to ensure it provides proper isolation."""
from pathlib import Path

from dpost.pc_plugins.test_pc.plugin import TestPCPlugin
from dpost.pc_plugins.test_pc.settings import build_config as build_pc_config


def test_test_pc_plugin_basic_functionality():
    plugin = TestPCPlugin()
    config = plugin.get_config()

    assert config.identifier == "test_pc"
    assert config.name == "TEST_PC"
    assert config.location == "Test Lab"
    assert tuple(config.active_device_plugins) == ("test_device",)


def test_test_pc_plugin_path_overrides(tmp_path):
    override_paths = {
        "app_dir": tmp_path / "app",
        "watch_dir": tmp_path / "upload",
        "dest_dir": tmp_path / "data",
        "rename_dir": tmp_path / "data" / "rename",
        "exceptions_dir": tmp_path / "data" / "exceptions",
        "daily_records_json": tmp_path / "records.json",
    }

    config = build_pc_config(override_paths=override_paths)

    assert config.paths.watch_dir == override_paths["watch_dir"]
    assert config.paths.dest_dir == override_paths["dest_dir"]
    assert config.paths.rename_dir == override_paths["rename_dir"]
    assert config.paths.exceptions_dir == override_paths["exceptions_dir"]


def test_test_pc_config_attributes():
    config = build_pc_config()
    assert isinstance(config.paths.watch_dir, Path)
    assert isinstance(config.paths.dest_dir, Path)
    assert config.active_device_plugins == ("test_device",)
