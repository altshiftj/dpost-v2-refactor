"""Unit coverage for canonical device plugin wrapper registration modules."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field

import pytest


@dataclass
class _RegistrySpy:
    """Capture plugin registry registrations for assertion."""

    calls: list[tuple[str, type[object]]] = field(default_factory=list)

    def register(self, name: str, plugin_type: type[object]) -> None:
        """Record the plugin registration call."""
        self.calls.append((name, plugin_type))


_PLUGIN_CASES: tuple[tuple[str, str, str], ...] = (
    ("dpost.device_plugins.dsv_horiba.plugin", "DSVHoribaPlugin", "dsv_horiba"),
    ("dpost.device_plugins.erm_hioki.plugin", "HiokiAnalyzerPlugin", "erm_hioki"),
    ("dpost.device_plugins.extr_haake.plugin", "EXTRHaakePlugin", "extr_haake"),
    ("dpost.device_plugins.psa_horiba.plugin", "PSAHoribaPlugin", "psa_horiba"),
    ("dpost.device_plugins.rhe_kinexus.plugin", "RheKinexusPlugin", "rhe_kinexus"),
    (
        "dpost.device_plugins.rmx_eirich_el1.plugin",
        "EirichMixerEL1Plugin",
        "rmx_eirich_el1",
    ),
    (
        "dpost.device_plugins.rmx_eirich_r01.plugin",
        "EirichMixerR01Plugin",
        "rmx_eirich_r01",
    ),
    ("dpost.device_plugins.sem_phenomxl2.plugin", "SEMPhenomXL2Plugin", "sem_phenomxl2"),
    ("dpost.device_plugins.test_device.plugin", "TestDevicePlugin", "test_device"),
    ("dpost.device_plugins.utm_zwick.plugin", "UTMZwickPlugin", "utm_zwick"),
)


@pytest.mark.parametrize(
    ("module_name", "plugin_class_name", "device_name"),
    _PLUGIN_CASES,
)
def test_device_plugin_wrapper_exposes_config_and_processor(
    module_name: str,
    plugin_class_name: str,
    device_name: str,
) -> None:
    """Ensure plugin wrapper classes expose stable config and processor handles."""
    module = importlib.import_module(module_name)
    plugin_type = getattr(module, plugin_class_name)
    plugin = plugin_type()

    assert plugin_type.__test__ is False
    assert plugin.get_config().identifier == device_name
    assert plugin.get_file_processor() is plugin.get_file_processor()


@pytest.mark.parametrize(
    ("module_name", "plugin_class_name", "device_name"),
    _PLUGIN_CASES,
)
def test_device_plugin_wrapper_registers_expected_plugin_type(
    module_name: str,
    plugin_class_name: str,
    device_name: str,
) -> None:
    """Ensure registration hooks map canonical names to wrapper plugin classes."""
    module = importlib.import_module(module_name)
    plugin_type = getattr(module, plugin_class_name)
    registry = _RegistrySpy()

    module.register_device_plugins(registry)

    assert registry.calls == [(device_name, plugin_type)]
