# PC to Device mapping configuration
# This defines which devices are associated with each PC type

PC_DEVICE_MAP = {
    "test_pc": ["test_device"],
    "tischrem_blb": ["sem_phenomxl2"],
    "zwick_blb": ["utm_zwick"],
    "horiba_blb": ["psa_horiba", "dsv_horiba"],
}

def get_devices_for_pc(pc_name: str) -> list[str]:
    """
    Get the list of device names for a given PC name.
    Returns a list of device plugin names that should be loaded for this PC.
    
    Args:
        pc_name: The PC plugin name (e.g., 'lab_workstation_blb')
        
    Returns:
        List of device plugin names
    """
    return PC_DEVICE_MAP.get(pc_name, ["sem_phenomxl2"])
