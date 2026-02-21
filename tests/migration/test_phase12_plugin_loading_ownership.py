"""Migration tests for dpost plugin-loading ownership boundaries."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_RUNTIME_BOOTSTRAP_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "runtime" / "bootstrap.py"
)
DPOST_SOURCE_ROOT = PROJECT_ROOT / "src" / "dpost"
DPOST_PLUGIN_LOADING_PATH = PROJECT_ROOT / "src" / "dpost" / "plugins" / "loading.py"
DPOST_PLUGIN_SYSTEM_PATH = PROJECT_ROOT / "src" / "dpost" / "plugins" / "system.py"
DPOST_PLUGIN_LEGACY_COMPAT_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "plugins" / "legacy_compat.py"
)


def test_runtime_bootstrap_has_no_direct_legacy_loader_dependency() -> None:
    """Require runtime bootstrap to resolve plugins via dpost plugin boundaries."""
    bootstrap_contents = DPOST_RUNTIME_BOOTSTRAP_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.loader" not in bootstrap_contents


def test_plugin_loading_boundaries_use_dpost_owned_plugin_contract_types() -> None:
    """Require dpost plugin loading/modules to avoid legacy plugin base imports."""
    loading_contents = DPOST_PLUGIN_LOADING_PATH.read_text(encoding="utf-8")
    system_contents = DPOST_PLUGIN_SYSTEM_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.device_plugins.device_plugin" not in loading_contents
    assert "ipat_watchdog.pc_plugins.pc_plugin" not in loading_contents
    assert "ipat_watchdog.device_plugins.device_plugin" not in system_contents
    assert "ipat_watchdog.pc_plugins.pc_plugin" not in system_contents


def test_plugin_system_uses_dpost_owned_plugin_namespace_groups() -> None:
    """Require plugin discovery/runtime groups to be dpost-owned by default."""
    system_contents = DPOST_PLUGIN_SYSTEM_PATH.read_text(encoding="utf-8")

    assert '_PLUGIN_NAMESPACE = "dpost"' in system_contents
    assert 'DEVICE_ENTRYPOINT_GROUP = "dpost.device_plugins"' in system_contents
    assert 'PC_ENTRYPOINT_GROUP = "dpost.pc_plugins"' in system_contents


def test_dpost_sources_have_no_legacy_namespace_literals() -> None:
    """Require complete retirement of legacy namespace literals in dpost source."""
    files_with_legacy_namespace: list[str] = []
    for python_path in DPOST_SOURCE_ROOT.rglob("*.py"):
        contents = python_path.read_text(encoding="utf-8")
        if "ipat_watchdog" in contents:
            files_with_legacy_namespace.append(
                str(python_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            )

    assert files_with_legacy_namespace == []


def test_legacy_plugin_compat_module_is_retired() -> None:
    """Require dpost plugin compat module removal after full namespace rehost."""
    assert not DPOST_PLUGIN_LEGACY_COMPAT_PATH.exists()


def test_device_plugin_contract_requires_file_processor_accessor() -> None:
    """Require device plugin protocol to include processor-construction contract."""

    class MissingProcessorPlugin:
        def get_config(self) -> object:
            return object()

    from dpost.plugins.contracts import DevicePlugin

    assert isinstance(MissingProcessorPlugin(), DevicePlugin) is False


def test_dpost_plugin_loading_resolves_reference_pc_devices() -> None:
    """Require dpost plugin-loading boundary to resolve reference PC devices."""
    from dpost.plugins.loading import get_devices_for_pc

    assert get_devices_for_pc("test_pc") == ["test_device"]


def test_reference_plugins_load_from_dpost_namespaces(monkeypatch) -> None:
    """Require reference plugin loading to resolve canonical dpost plugin modules."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.device_plugins.test_device.plugin",
        "dpost.pc_plugins.test_pc.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_device_plugin, load_pc_plugin

    pc_plugin = load_pc_plugin("test_pc")
    device_plugin = load_device_plugin("test_device")

    assert "dpost.pc_plugins.test_pc.plugin" in sys.modules
    assert "dpost.device_plugins.test_device.plugin" in sys.modules
    assert pc_plugin.__class__.__module__ == "dpost.pc_plugins.test_pc.plugin"
    assert (
        device_plugin.__class__.__module__ == "dpost.device_plugins.test_device.plugin"
    )


def test_dpost_plugin_loader_unknown_plugin_message_is_actionable() -> None:
    """Require dpost plugin-loading boundary errors to remain actionable."""
    from dpost.plugins.loading import load_device_plugin

    with pytest.raises(RuntimeError) as exc_info:
        load_device_plugin("missing-device")

    error_message = str(exc_info.value)
    assert "missing-device" in error_message
    assert "available device plugins" in error_message.lower()
    assert "test_device" in error_message


def test_concrete_utm_zwick_plugin_loads_from_dpost_namespace(monkeypatch) -> None:
    """Require concrete UTM plugin loading to resolve canonical dpost module."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.device_plugins.utm_zwick.plugin",
        "ipat_watchdog.device_plugins.utm_zwick.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_device_plugin

    plugin = load_device_plugin("utm_zwick")

    assert plugin.__class__.__module__ == "dpost.device_plugins.utm_zwick.plugin"
    assert "dpost.device_plugins.utm_zwick.plugin" in sys.modules


def test_concrete_zwick_blb_pc_plugin_loads_from_dpost_namespace(monkeypatch) -> None:
    """Require concrete Zwick BLB PC plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.pc_plugins.zwick_blb.plugin",
        "ipat_watchdog.pc_plugins.zwick_blb.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_pc_plugin

    plugin = load_pc_plugin("zwick_blb")

    assert plugin.__class__.__module__ == "dpost.pc_plugins.zwick_blb.plugin"
    assert "dpost.pc_plugins.zwick_blb.plugin" in sys.modules


def test_concrete_extr_haake_plugin_loads_from_dpost_namespace(monkeypatch) -> None:
    """Require concrete EXTR HAAKE plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.device_plugins.extr_haake.plugin",
        "ipat_watchdog.device_plugins.extr_haake.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_device_plugin

    plugin = load_device_plugin("extr_haake")

    assert plugin.__class__.__module__ == "dpost.device_plugins.extr_haake.plugin"
    assert "dpost.device_plugins.extr_haake.plugin" in sys.modules


def test_concrete_haake_blb_pc_plugin_loads_from_dpost_namespace(monkeypatch) -> None:
    """Require concrete HAAKE BLB PC plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.pc_plugins.haake_blb.plugin",
        "ipat_watchdog.pc_plugins.haake_blb.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_pc_plugin

    plugin = load_pc_plugin("haake_blb")

    assert plugin.__class__.__module__ == "dpost.pc_plugins.haake_blb.plugin"
    assert "dpost.pc_plugins.haake_blb.plugin" in sys.modules


def test_concrete_erm_hioki_plugin_loads_from_dpost_namespace(monkeypatch) -> None:
    """Require concrete ERM HIOKI plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.device_plugins.erm_hioki.plugin",
        "ipat_watchdog.device_plugins.erm_hioki.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_device_plugin

    plugin = load_device_plugin("erm_hioki")

    assert plugin.__class__.__module__ == "dpost.device_plugins.erm_hioki.plugin"
    assert "dpost.device_plugins.erm_hioki.plugin" in sys.modules


def test_concrete_hioki_blb_pc_plugin_loads_from_dpost_namespace(monkeypatch) -> None:
    """Require concrete HIOKI BLB PC plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.pc_plugins.hioki_blb.plugin",
        "ipat_watchdog.pc_plugins.hioki_blb.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_pc_plugin

    plugin = load_pc_plugin("hioki_blb")

    assert plugin.__class__.__module__ == "dpost.pc_plugins.hioki_blb.plugin"
    assert "dpost.pc_plugins.hioki_blb.plugin" in sys.modules


def test_concrete_sem_phenomxl2_plugin_loads_from_dpost_namespace(
    monkeypatch,
) -> None:
    """Require concrete SEM PHENOM XL2 plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.device_plugins.sem_phenomxl2.plugin",
        "ipat_watchdog.device_plugins.sem_phenomxl2.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_device_plugin

    plugin = load_device_plugin("sem_phenomxl2")

    assert plugin.__class__.__module__ == "dpost.device_plugins.sem_phenomxl2.plugin"
    assert "dpost.device_plugins.sem_phenomxl2.plugin" in sys.modules


def test_concrete_tischrem_blb_pc_plugin_loads_from_dpost_namespace(
    monkeypatch,
) -> None:
    """Require concrete TISCHREM BLB PC plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.pc_plugins.tischrem_blb.plugin",
        "ipat_watchdog.pc_plugins.tischrem_blb.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_pc_plugin

    plugin = load_pc_plugin("tischrem_blb")

    assert plugin.__class__.__module__ == "dpost.pc_plugins.tischrem_blb.plugin"
    assert "dpost.pc_plugins.tischrem_blb.plugin" in sys.modules


def test_concrete_rmx_eirich_el1_plugin_loads_from_dpost_namespace(
    monkeypatch,
) -> None:
    """Require concrete RMX EIRICH EL1 plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.device_plugins.rmx_eirich_el1.plugin",
        "ipat_watchdog.device_plugins.rmx_eirich_el1.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_device_plugin

    plugin = load_device_plugin("rmx_eirich_el1")

    assert plugin.__class__.__module__ == "dpost.device_plugins.rmx_eirich_el1.plugin"
    assert "dpost.device_plugins.rmx_eirich_el1.plugin" in sys.modules


def test_concrete_rmx_eirich_r01_plugin_loads_from_dpost_namespace(
    monkeypatch,
) -> None:
    """Require concrete RMX EIRICH R01 plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.device_plugins.rmx_eirich_r01.plugin",
        "ipat_watchdog.device_plugins.rmx_eirich_r01.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_device_plugin

    plugin = load_device_plugin("rmx_eirich_r01")

    assert plugin.__class__.__module__ == "dpost.device_plugins.rmx_eirich_r01.plugin"
    assert "dpost.device_plugins.rmx_eirich_r01.plugin" in sys.modules


def test_concrete_eirich_blb_pc_plugin_loads_from_dpost_namespace(monkeypatch) -> None:
    """Require concrete EIRICH BLB PC plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.pc_plugins.eirich_blb.plugin",
        "ipat_watchdog.pc_plugins.eirich_blb.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_pc_plugin

    plugin = load_pc_plugin("eirich_blb")

    assert plugin.__class__.__module__ == "dpost.pc_plugins.eirich_blb.plugin"
    assert "dpost.pc_plugins.eirich_blb.plugin" in sys.modules


def test_concrete_dsv_horiba_plugin_loads_from_dpost_namespace(monkeypatch) -> None:
    """Require concrete DSV HORIBA plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.device_plugins.dsv_horiba.plugin",
        "ipat_watchdog.device_plugins.dsv_horiba.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_device_plugin

    plugin = load_device_plugin("dsv_horiba")

    assert plugin.__class__.__module__ == "dpost.device_plugins.dsv_horiba.plugin"
    assert "dpost.device_plugins.dsv_horiba.plugin" in sys.modules


def test_concrete_psa_horiba_plugin_loads_from_dpost_namespace(monkeypatch) -> None:
    """Require concrete PSA HORIBA plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.device_plugins.psa_horiba.plugin",
        "ipat_watchdog.device_plugins.psa_horiba.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_device_plugin

    plugin = load_device_plugin("psa_horiba")

    assert plugin.__class__.__module__ == "dpost.device_plugins.psa_horiba.plugin"
    assert "dpost.device_plugins.psa_horiba.plugin" in sys.modules


def test_concrete_horiba_blb_pc_plugin_loads_from_dpost_namespace(monkeypatch) -> None:
    """Require concrete HORIBA BLB PC plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.pc_plugins.horiba_blb.plugin",
        "ipat_watchdog.pc_plugins.horiba_blb.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_pc_plugin

    plugin = load_pc_plugin("horiba_blb")

    assert plugin.__class__.__module__ == "dpost.pc_plugins.horiba_blb.plugin"
    assert "dpost.pc_plugins.horiba_blb.plugin" in sys.modules


def test_concrete_rhe_kinexus_plugin_loads_from_dpost_namespace(monkeypatch) -> None:
    """Require concrete RHE KINEXUS plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.device_plugins.rhe_kinexus.plugin",
        "ipat_watchdog.device_plugins.rhe_kinexus.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_device_plugin

    plugin = load_device_plugin("rhe_kinexus")

    assert plugin.__class__.__module__ == "dpost.device_plugins.rhe_kinexus.plugin"
    assert "dpost.device_plugins.rhe_kinexus.plugin" in sys.modules


def test_concrete_kinexus_blb_pc_plugin_loads_from_dpost_namespace(monkeypatch) -> None:
    """Require concrete KINEXUS BLB PC plugin to load from dpost namespace."""
    system_module = importlib.import_module("dpost.plugins.system")
    monkeypatch.setattr(system_module, "_PLUGIN_LOADER_SINGLETON", None)
    for module_name in (
        "dpost.pc_plugins.kinexus_blb.plugin",
        "ipat_watchdog.pc_plugins.kinexus_blb.plugin",
    ):
        sys.modules.pop(module_name, None)

    from dpost.plugins.loading import load_pc_plugin

    plugin = load_pc_plugin("kinexus_blb")

    assert plugin.__class__.__module__ == "dpost.pc_plugins.kinexus_blb.plugin"
    assert "dpost.pc_plugins.kinexus_blb.plugin" in sys.modules
