import pytest

from ipat_watchdog.core.config import PCConfig
from ipat_watchdog.loader import load_pc_plugin
from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin


def _load_plugin_or_skip(name: str) -> PCPlugin:
    try:
        return load_pc_plugin(name)
    except RuntimeError as exc:
        pytest.skip(f"PC plugin {name!r} not available: {exc}")


@pytest.mark.parametrize(
    "plugin_name, expectations",
    [
        (
            "test_pc",
            {
                "identifier": "test_pc",
                "devices": ("test_device",),
                "watch_dir_suffix": "Upload",
                "dest_dir_suffix": "Data",
            },
        ),
        (
            "twinscrew_blb",
            {
                "identifier": "twinscrew_blb",
                "devices": ("etr_twinscrew",),
            },
        ),
        (
            "kinexus_blb",
            {
                "identifier": "kinexus_blb",
                "devices": ("rhe_kinexus",),
            },
        ),
        ("tischrem_blb", {}),
    ],
)
def test_load_pc_plugins(plugin_name: str, expectations: dict[str, object]):
    plugin = _load_plugin_or_skip(plugin_name)
    assert isinstance(plugin, PCPlugin)

    config = plugin.get_config()
    assert isinstance(config, PCConfig)

    if "identifier" in expectations:
        assert config.identifier == expectations["identifier"]
    if "devices" in expectations:
        assert config.active_device_plugins == expectations["devices"]
    if "watch_dir_suffix" in expectations:
        assert str(config.paths.watch_dir).endswith(str(expectations["watch_dir_suffix"]))
    if "dest_dir_suffix" in expectations:
        assert str(config.paths.dest_dir).endswith(str(expectations["dest_dir_suffix"]))


def test_pc_plugin_not_found():
    with pytest.raises(RuntimeError, match="No PC plugin named 'nonexistent'"):
        load_pc_plugin("nonexistent")
