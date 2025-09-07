import pytest
from ipat_watchdog.loader import get_devices_for_pc

def test_pc_device_mapping():
    """Test the PC-device mapping functionality through PC settings."""
    # Test actual mappings via PC settings
    assert get_devices_for_pc("test_pc") == ["test_device"]
    assert get_devices_for_pc("tischrem_blb") == ["sem_phenomxl2"]
    assert get_devices_for_pc("zwick_blb") == ["utm_zwick"]
    assert get_devices_for_pc("horiba_blb") == ["psa_horiba", "dsv_horiba"]

def test_pc_plugin_not_found():
    """Test error handling for non-existent PC plugin."""
    with pytest.raises(RuntimeError, match="No PC plugin named 'unknown_pc'"):
        get_devices_for_pc("unknown_pc")

def test_mapping_completeness():
    """Test that all PC plugins have device mappings."""
    pc_names = ["test_pc", "tischrem_blb", "zwick_blb", "horiba_blb"]
    
    for pc_name in pc_names:
        devices = get_devices_for_pc(pc_name)
        assert isinstance(devices, list)
        assert len(devices) > 0
        assert all(isinstance(device, str) for device in devices)
