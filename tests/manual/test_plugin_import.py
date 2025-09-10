#!/usr/bin/env python3


import os
import traceback
print("Step 1: Testing individual instantiation...")

try:
    from ipat_watchdog.device_plugins.sem_phenomxl2.settings import SEMPhenomXL2Settings
    settings = SEMPhenomXL2Settings()
    print("✓ SEMPhenomXL2Settings instantiated")
except Exception as e:
    print("✗ SEMPhenomXL2Settings instantiation failed:", e)
    traceback.print_exc()

try:
    from ipat_watchdog.device_plugins.sem_phenomxl2.file_processor import FileProcessorSEMPhenomXL2
    processor = FileProcessorSEMPhenomXL2()
    print("✓ FileProcessorSEMPhenomXL2 instantiated")
except Exception as e:
    print("✗ FileProcessorSEMPhenomXL2 instantiation failed:", e)
    traceback.print_exc()

print("\nStep 2: Creating plugin class manually...")

try:
    from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
    from ipat_watchdog.device_plugins.sem_phenomxl2.settings import SEMPhenomXL2Settings
    from ipat_watchdog.device_plugins.sem_phenomxl2.file_processor import FileProcessorSEMPhenomXL2
    class SEMPhenomXL2Plugin(DevicePlugin):
        def __init__(self):
            self._settings = SEMPhenomXL2Settings()
            self._processor = FileProcessorSEMPhenomXL2()
        def get_settings(self):
            return self._settings
        def get_file_processor(self):
            return self._processor
    plugin = SEMPhenomXL2Plugin()
    print("✓ SEMPhenomXL2Plugin instantiated and methods available:")
    print("  get_settings:", plugin.get_settings())
    print("  get_file_processor:", plugin.get_file_processor())
except Exception as e:
    print("✗ SEMPhenomXL2Plugin instantiation failed:", e)
    traceback.print_exc()

print("\nStep 3: Checking plugin file content...")

plugin_path = "src/ipat_watchdog/device_plugins/sem_phenomxl2/plugin.py"
if os.path.exists(plugin_path):
    print(f"✓ Plugin file exists: {plugin_path}")
    with open(plugin_path, "r", encoding="utf-8") as f:
        content = f.read()
        print("--- Plugin file content (first 10 lines) ---")
        print("\n".join(content.splitlines()[:10]))
else:
    print(f"✗ Plugin file does not exist: {plugin_path}")
