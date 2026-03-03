"""Manual smoke checks for SEM plugin construction and file presence."""

from __future__ import annotations

from pathlib import Path

import pytest

from dpost.application.config import DeviceConfig
from dpost.device_plugins.sem_phenomxl2.file_processor import FileProcessorSEMPhenomXL2
from dpost.device_plugins.sem_phenomxl2.settings import build_config
from dpost.plugins.contracts import DevicePlugin

pytestmark = pytest.mark.manual


def test_sem_plugin_config_and_processor_instantiation() -> None:
    """Manual smoke test for SEM config + processor instantiation."""
    device_config = build_config()
    assert device_config.identifier

    processor = FileProcessorSEMPhenomXL2(device_config)
    assert isinstance(processor, FileProcessorSEMPhenomXL2)


def test_sem_plugin_contract_shape() -> None:
    """Manual smoke test for DevicePlugin contract compatibility."""

    class SEMPhenomXL2Plugin(DevicePlugin):
        def __init__(self) -> None:
            self._config: DeviceConfig = build_config()
            self._processor = FileProcessorSEMPhenomXL2(self._config)

        def get_config(self) -> DeviceConfig:
            return self._config

        def get_file_processor(self) -> FileProcessorSEMPhenomXL2:
            return self._processor

    plugin = SEMPhenomXL2Plugin()
    assert plugin.get_config().identifier
    assert isinstance(plugin.get_file_processor(), FileProcessorSEMPhenomXL2)


def test_sem_plugin_file_exists() -> None:
    """Manual smoke test to ensure the plugin module file is present."""
    plugin_path = Path("src/dpost/device_plugins/sem_phenomxl2/plugin.py")
    assert plugin_path.exists()
