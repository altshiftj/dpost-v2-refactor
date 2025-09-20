import pytest

from ipat_watchdog.loader import get_devices_for_pc


_EXPECTED_MAPPINGS = [
    ("test_pc", ["test_device"]),
    ("tischrem_blb", ["sem_phenomxl2"]),
    ("zwick_blb", ["utm_zwick"]),
    ("horiba_blb", ["psa_horiba", "dsv_horiba"]),
]


def _load_devices_or_skip(pc_name: str) -> list[str]:
    try:
        return get_devices_for_pc(pc_name)
    except RuntimeError as exc:
        pytest.skip(f"PC plugin {pc_name!r} not available: {exc}")


@pytest.mark.parametrize("pc_name, expected", _EXPECTED_MAPPINGS)
def test_pc_device_mapping(pc_name: str, expected: list[str]):
    assert _load_devices_or_skip(pc_name) == expected


@pytest.mark.parametrize("pc_name", [name for name, _ in _EXPECTED_MAPPINGS])
def test_mapping_completeness(pc_name: str):
    devices = _load_devices_or_skip(pc_name)
    assert isinstance(devices, list)
    assert devices
    assert all(isinstance(device, str) for device in devices)


def test_pc_plugin_not_found():
    with pytest.raises(RuntimeError, match="No PC plugin named 'unknown_pc'"):
        get_devices_for_pc("unknown_pc")
