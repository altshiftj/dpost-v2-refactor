import pytest

from ipat_watchdog.core.config import PCConfig
from ipat_watchdog.loader import load_pc_plugin
from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin


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
            "eirich_blb",
            {
                "identifier": "eirich_blb",
                "devices": ("rmx_eirich_el1", "rmx_eirich_r01"),
            },
        ),
        (
            "haake_blb",
            {
                "identifier": "haake_blb",
                "devices": ("extr_haake",),
            },
        ),
        (
            "hioki_blb",
            {
                "identifier": "hioki_blb",
                "devices": ("erm_hioki",),
            },
        ),
        (
            "horiba_blb",
            {
                "identifier": "horiba_blb",
                "devices": ("psa_horiba", "dsv_horiba"),
            },
        ),
        (
            "kinexus_blb",
            {
                "identifier": "kinexus_blb",
                "devices": ("rhe_kinexus",),
            },
        ),
        (
            "tischrem_blb",
            {
                "identifier": "tischrem_blb",
                "devices": ("sem_phenomxl2",),
            },
        ),
        (
            "zwick_blb",
            {
                "identifier": "zwick_blb",
                "devices": ("utm_zwick",),
            },
        ),
    ],
)
def test_load_pc_plugins(plugin_name: str, expectations: dict[str, object]) -> None:
    """Load each canonical PC plugin and validate expected config fields."""
    plugin = load_pc_plugin(plugin_name)
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


def test_pc_plugin_not_found() -> None:
    """Raise runtime error for unknown PC plugin identifiers."""
    with pytest.raises(RuntimeError, match="No PC plugin named 'nonexistent'"):
        load_pc_plugin("nonexistent")
