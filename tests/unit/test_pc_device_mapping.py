import pytest
from ipat_watchdog.pc_device_mapping import get_devices_for_pc, PC_DEVICE_MAP

def test_pc_device_mapping():
    """Test the PC-device mapping functionality."""
    # Test known mappings
    assert get_devices_for_pc("default_pc_blb") == ["sem_phenomxl2"]
    assert get_devices_for_pc("lab_workstation_blb") == ["sem_phenomxl2", "psa_horibalinks_blb"]
    assert get_devices_for_pc("office_desktop_blb") == ["utm_zwick"]
    assert get_devices_for_pc("server_backend_blb") == ["sem_phenomxl2", "psa_horibalinks_blb", "utm_zwick"]
    
    # Test unknown PC - should fallback to default
    assert get_devices_for_pc("unknown_pc") == ["sem_phenomxl2"]

def test_loader_integration():
    """Test that the loader function works correctly."""
    from ipat_watchdog.loader import get_devices_for_pc as loader_get_devices
    
    # Should return same results as direct mapping
    assert loader_get_devices("default_pc_blb") == ["sem_phenomxl2"]
    assert loader_get_devices("lab_workstation_blb") == ["sem_phenomxl2", "psa_horibalinks_blb"]

def test_mapping_completeness():
    """Test that all PCs have at least one device."""
    for pc_name, devices in PC_DEVICE_MAP.items():
        assert isinstance(devices, list)
        assert len(devices) > 0
        assert all(isinstance(device, str) for device in devices)
