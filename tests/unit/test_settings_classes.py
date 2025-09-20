from ipat_watchdog.pc_plugins.test_pc.settings import build_config as build_pc_config
from ipat_watchdog.device_plugins.test_device.settings import build_config as build_device_config


def test_pc_config_defaults():
    config = build_pc_config()
    assert config.identifier == "test_pc"
    assert config.active_device_plugins == ("test_device",)
    assert config.paths.watch_dir.name == "Upload"
    assert config.naming.id_separator == "-"


def test_device_config_defaults():
    config = build_device_config()
    assert config.identifier == "test_device"
    assert ".tif" in config.files.allowed_extensions
    assert config.metadata.device_abbr == "TEST"
