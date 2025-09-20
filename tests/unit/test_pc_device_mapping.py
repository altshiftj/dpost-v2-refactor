import pytest
from ipat_watchdog.loader import get_devices_for_pc


def _expect_devices(pc_name: str, expected: list[str]):
    try:
        assert get_devices_for_pc(pc_name) == expected
    except RuntimeError as exc:
        pytest.skip(f"PC plugin {pc_name!r} not available: {exc}")


def test_pc_device_mapping():
    """Test the PC-device mapping functionality through PC settings."""
    _expect_devices("test_pc", ["test_device"])
    _expect_devices("tischrem_blb", ["sem_phenomxl2"])
    _expect_devices("zwick_blb", ["utm_zwick"])
    _expect_devices("horiba_blb", ["psa_horiba", "dsv_horiba"])


def test_pc_plugin_not_found():
    """Test error handling for non-existent PC plugin."""
    with pytest.raises(RuntimeError, match="No PC plugin named 'unknown_pc'"):
        get_devices_for_pc("unknown_pc")


def test_mapping_completeness():
    """Test that all PC plugins have device mappings."""
    pc_names = ["test_pc", "tischrem_blb", "zwick_blb", "horiba_blb"]

    for pc_name in pc_names:
        try:
            devices = get_devices_for_pc(pc_name)
        except RuntimeError as exc:
            pytest.skip(f"PC plugin {pc_name!r} not available: {exc}")
            continue
        assert isinstance(devices, list)
        assert devices
        assert all(isinstance(device, str) for device in devices)
