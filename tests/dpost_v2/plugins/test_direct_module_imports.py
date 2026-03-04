from __future__ import annotations

import dpost_v2.plugins.contracts as plugin_contracts
import dpost_v2.plugins.devices._device_template.processor as template_processor_module


def test_plugins_contracts_direct_module_import_exposes_contract_surface() -> None:
    assert plugin_contracts.PLUGIN_CONTRACT_VERSION
    assert "RuntimeContext" in plugin_contracts.__all__
    assert callable(plugin_contracts.require_contract_version_compatible)


def test_template_processor_direct_module_import_exposes_processor_types() -> None:
    assert hasattr(template_processor_module, "TemplateDeviceProcessor")
    assert hasattr(template_processor_module, "DeviceProcessorFormatError")
    assert hasattr(template_processor_module, "DeviceProcessorValidationError")
