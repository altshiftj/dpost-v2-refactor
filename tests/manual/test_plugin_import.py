#!/usr/bin/env python3

import os
import traceback

print("Step 1: Testing config + processor instantiation...")

try:
    from dpost.device_plugins.sem_phenomxl2.file_processor import \
        FileProcessorSEMPhenomXL2
    from dpost.device_plugins.sem_phenomxl2.settings import \
        build_config

    device_config = build_config()
    print("[OK] build_config() returned DeviceConfig with id:", device_config.identifier)

    processor = FileProcessorSEMPhenomXL2(device_config)
    print("[OK] FileProcessorSEMPhenomXL2 instantiated with DeviceConfig")
except Exception as e:
    print("[FAIL] Config/Processor instantiation failed:", e)
    traceback.print_exc()

print("\nStep 2: Creating plugin class manually (mirrors runtime plugin)...")

try:
    from dpost.application.config import DeviceConfig
    from dpost.device_plugins.sem_phenomxl2.file_processor import \
        FileProcessorSEMPhenomXL2
    from dpost.device_plugins.sem_phenomxl2.settings import \
        build_config
    from dpost.plugins.contracts import DevicePlugin

    class SEMPhenomXL2Plugin(DevicePlugin):
        def __init__(self) -> None:
            self._config: DeviceConfig = build_config()
            self._processor = FileProcessorSEMPhenomXL2(self._config)

        def get_config(self) -> DeviceConfig:
            return self._config

        def get_file_processor(self):
            return self._processor

    plugin = SEMPhenomXL2Plugin()
    print("[OK] SEMPhenomXL2Plugin instantiated and methods available:")
    print("  get_config.identifier:", plugin.get_config().identifier)
    print("  get_file_processor:", type(plugin.get_file_processor()).__name__)
except Exception as e:
    print("[FAIL] SEMPhenomXL2Plugin instantiation failed:", e)
    traceback.print_exc()

print("\nStep 3: Checking plugin file content...")

plugin_path = "src/dpost/device_plugins/sem_phenomxl2/plugin.py"
if os.path.exists(plugin_path):
    print(f"[OK] Plugin file exists: {plugin_path}")
    with open(plugin_path, "r", encoding="utf-8") as f:
        content = f.read()
        print("--- Plugin file content (first 10 lines) ---")
        print("\n".join(content.splitlines()[:10]))
else:
    print(f"[FAIL] Plugin file does not exist: {plugin_path}")
