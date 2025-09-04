#!/usr/bin/env python3

print("Step 1: Testing individual instantiation...")

try:
    from ipat_watchdog.device_plugins.sem_phenomxl2.settings import SEMPhenomXL2Settings
    settings = SEMPhenomXL2Settings()
    print("✓ SEMPhenomXL2Settings instantiated")
except Exception as e:
    print("✗ SEMPhenomXL2Settings instantiation failed:", e)
    import traceback
    traceback.print_exc()

try:
    from ipat_watchdog.device_plugins.sem_phenomxl2.file_processor import FileProcessorSEMPhenomXL2
    processor = FileProcessorSEMPhenomXL2()
    print("✓ FileProcessorSEMPhenomXL2 instantiated")
except Exception as e:
    print("✗ FileProcessorSEMPhenomXL2 instantiation failed:", e)
    import traceback
    traceback.print_exc()

print("\nStep 2: Creating plugin class manually...")

try:
    from ipat_watchdog.device_plugins.device_plugin import DevicePlugin
    from ipat_watchdog.device_plugins.sem_phenomxl2.settings import SEMPhenomXL2Settings
    from ipat_watchdog.device_plugins.sem_phenomxl2.file_processor import FileProcessorSEMPhenomXL2
    from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
    from ipat_watchdog.core.config.device_settings_base import DeviceSettings

    class TestSEMPhenomXL2Plugin(DevicePlugin):
        def __init__(self) -> None:
            self._settings = SEMPhenomXL2Settings()
            self._processor = FileProcessorSEMPhenomXL2()

        def get_settings(self) -> DeviceSettings:
            return self._settings

        def get_file_processor(self) -> FileProcessorABS:
            return self._processor

    plugin = TestSEMPhenomXL2Plugin()
    print("✓ Manual plugin creation successful")
    
except Exception as e:
    print("✗ Manual plugin creation failed:", e)
    import traceback
    traceback.print_exc()

print("\nStep 3: Checking plugin file content...")

import ast
import os

plugin_path = "src/ipat_watchdog/device_plugins/sem_phenomxl2/plugin.py"
if os.path.exists(plugin_path):
    with open(plugin_path, 'r') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
        print("✓ Plugin file syntax is valid")
        
        # Find class definitions
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        print(f"Classes found: {classes}")
        
    except SyntaxError as e:
        print(f"✗ Plugin file has syntax error: {e}")
else:
    print("✗ Plugin file not found")
