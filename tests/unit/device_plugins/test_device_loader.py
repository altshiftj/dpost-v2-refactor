import pytest

from dpost.application.config import DeviceConfig
from dpost.plugins.contracts import DevicePlugin
from dpost.plugins.loading import load_device_plugin


def _load_device_or_skip(name: str) -> DevicePlugin:
    try:
        return load_device_plugin(name)
    except RuntimeError as exc:
        pytest.skip(f"Device plugin {name!r} not available: {exc}")


@pytest.mark.parametrize(
    "device_name, expectations",
    [
        (
            "test_device",
            {
                "identifier": "test_device",
                "native_ext": {".tif"},
                "device_abbr": "TEST",
            },
        ),
        (
            "psa_horiba",
            {
                "identifier": "psa_horiba",
                "native_ext": {".ngb"},
                "export_ext": {".csv"},
                "device_abbr": "PSA",
            },
        ),
        (
            "rhe_kinexus",
            {
                "identifier": "rhe_kinexus",
                "native_ext": {".rdf"},
                "export_ext": {".csv"},
                "device_abbr": "RHE",
            },
        ),
    ],
)
def test_load_device_plugins(device_name: str, expectations: dict[str, object]):
    plugin = _load_device_or_skip(device_name)
    assert isinstance(plugin, DevicePlugin)

    config = plugin.get_config()
    assert isinstance(config, DeviceConfig)

    if "identifier" in expectations:
        assert config.identifier == expectations["identifier"]
    if "native_ext" in expectations:
        assert expectations["native_ext"].issubset(set(config.files.native_extensions))
    if "export_ext" in expectations:
        assert expectations["export_ext"].issubset(set(config.files.exported_extensions))
    if "device_abbr" in expectations:
        assert config.metadata.device_abbr == expectations["device_abbr"]


def test_device_plugin_not_found():
    with pytest.raises(RuntimeError, match="No device plugin named 'ghost_device'"):
        load_device_plugin("ghost_device")
