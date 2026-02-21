"""Migration guards for legacy-retirement progress in shared test harness files."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FAKE_UI_PATH = PROJECT_ROOT / "tests" / "helpers" / "fake_ui.py"
FAKE_SYNC_PATH = PROJECT_ROOT / "tests" / "helpers" / "fake_sync.py"
FAKE_PROCESS_MANAGER_PATH = (
    PROJECT_ROOT / "tests" / "helpers" / "fake_process_manager.py"
)
FAKE_PROCESSOR_PATH = PROJECT_ROOT / "tests" / "helpers" / "fake_processor.py"
CONFTEST_PATH = PROJECT_ROOT / "tests" / "conftest.py"
LEGACY_SOURCE_ROOT = PROJECT_ROOT / "src" / "ipat_watchdog"
DPOST_METRICS_PATH = PROJECT_ROOT / "src" / "dpost" / "application" / "metrics.py"
UNIT_OBSERVABILITY_TEST_PATH = PROJECT_ROOT / "tests" / "unit" / "test_observability.py"
UNIT_PC_DEVICE_MAPPING_TEST_PATH = (
    PROJECT_ROOT / "tests" / "unit" / "loader" / "test_pc_device_mapping.py"
)
UNIT_TEST_PLUGINS_INTEGRATION_PATH = (
    PROJECT_ROOT / "tests" / "unit" / "plugins" / "test_test_plugins_integration.py"
)
UNIT_PLUGIN_LOADER_TEST_PATH = (
    PROJECT_ROOT / "tests" / "unit" / "plugin_system" / "test_plugin_loader.py"
)
UNIT_PLUGIN_NO_DOUBLE_LOGGING_TEST_PATH = (
    PROJECT_ROOT / "tests" / "unit" / "plugin_system" / "test_no_double_logging.py"
)
UNIT_PC_PLUGINS_TEST_PATH = (
    PROJECT_ROOT / "tests" / "unit" / "pc_plugins" / "test_pc_plugins.py"
)
UNIT_TEST_PC_PLUGIN_TEST_PATH = (
    PROJECT_ROOT / "tests" / "unit" / "pc_plugins" / "test_test_pc_plugin.py"
)
UNIT_HAAKE_PC_PLUGIN_TEST_PATH = (
    PROJECT_ROOT / "tests" / "unit" / "pc_plugins" / "test_haake_pc_plugin.py"
)
DEVICE_PLUGIN_UNIT_TEST_PATHS = (
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "device_plugins"
    / "dsv_horiba"
    / "test_dsv_file_processor.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "device_plugins"
    / "erm_hioki"
    / "test_file_processor.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "device_plugins"
    / "mix_eirich"
    / "test_file_processor.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "device_plugins"
    / "psa_horiba"
    / "test_file_processor.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "device_plugins"
    / "psa_horiba"
    / "test_purge_and_reconstruct.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "device_plugins"
    / "psa_horiba"
    / "test_staging_rename_cancel.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "device_plugins"
    / "rhe_kinexus"
    / "test_file_processor.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "device_plugins"
    / "sem_phenomxl2"
    / "test_file_processor.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "device_plugins"
    / "utm_zwick"
    / "test_file_processor.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "device_plugins"
    / "extr_haake"
    / "test_plugin.py",
)
INTEGRATION_RUNTIME_TEST_PATHS = (
    PROJECT_ROOT / "tests" / "integration" / "test_integration.py",
    PROJECT_ROOT / "tests" / "integration" / "test_device_integrations.py",
    PROJECT_ROOT / "tests" / "integration" / "test_multi_processor_app_flow.py",
    PROJECT_ROOT / "tests" / "integration" / "test_extr_haake_safesave.py",
)
INTEGRATION_TEST_PATHS = (
    PROJECT_ROOT / "tests" / "integration" / "test_device_integrations.py",
    PROJECT_ROOT / "tests" / "integration" / "test_extr_haake_safesave.py",
    PROJECT_ROOT / "tests" / "integration" / "test_integration.py",
    PROJECT_ROOT / "tests" / "integration" / "test_multi_device_integration.py",
    PROJECT_ROOT / "tests" / "integration" / "test_multi_processor_app_flow.py",
    PROJECT_ROOT / "tests" / "integration" / "test_settings_integration.py",
    PROJECT_ROOT / "tests" / "integration" / "test_utm_zwick_integration.py",
)
CORE_DATAFLOW_UNIT_TEST_PATHS = (
    PROJECT_ROOT / "tests" / "unit" / "core" / "records" / "test_local_record.py",
    PROJECT_ROOT / "tests" / "unit" / "core" / "records" / "test_record_manager.py",
    PROJECT_ROOT / "tests" / "unit" / "core" / "session" / "test_session_manager.py",
    PROJECT_ROOT / "tests" / "unit" / "core" / "storage" / "test_filesystem_utils.py",
    PROJECT_ROOT / "tests" / "unit" / "core" / "sync" / "test_sync_kadi.py",
)
CORE_PROCESSING_SETTINGS_UNIT_TEST_PATHS = (
    PROJECT_ROOT / "tests" / "unit" / "core" / "processing" / "test_device_resolver.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "core"
    / "processing"
    / "test_device_resolver_eirich_variants.py",
    PROJECT_ROOT / "tests" / "unit" / "core" / "processing" / "test_error_handling.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "core"
    / "processing"
    / "test_file_process_manager.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "core"
    / "processing"
    / "test_force_paths_kadi_sync.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "core"
    / "processing"
    / "test_modified_event_gate.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "core"
    / "processing"
    / "test_stability_tracker.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "core"
    / "settings"
    / "test_composite_settings.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "core"
    / "settings"
    / "test_device_settings_base.py",
    PROJECT_ROOT / "tests" / "unit" / "core" / "settings" / "test_settings_classes.py",
    PROJECT_ROOT / "tests" / "unit" / "core" / "settings" / "test_settings_manager.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "core"
    / "settings"
    / "test_stability_tracker_overrides.py",
)
REMAINING_TEST_IMPORT_SWEEP_PATHS = (
    PROJECT_ROOT / "tests" / "conftest.py",
    PROJECT_ROOT / "tests" / "manual" / "test_plugin_import.py",
    PROJECT_ROOT / "tests" / "manual" / "test_sync_integration.py",
    PROJECT_ROOT / "tests" / "unit" / "core" / "app" / "test_bootstrap.py",
    PROJECT_ROOT / "tests" / "unit" / "core" / "ui" / "test_dialogs.py",
    PROJECT_ROOT / "tests" / "unit" / "core" / "ui" / "test_ui_tkinter.py",
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "device_plugins"
    / "erm_hioki"
    / "test_live_run_sequence.py",
    PROJECT_ROOT / "tests" / "unit" / "device_plugins" / "test_device_loader.py",
)


def test_fake_ui_helper_avoids_legacy_interaction_imports() -> None:
    """Require shared headless UI test helper to avoid legacy interaction imports."""
    contents = FAKE_UI_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.interactions" not in contents


def test_fake_sync_helper_avoids_legacy_sync_imports() -> None:
    """Require shared sync test helper to avoid legacy sync abstract imports."""
    contents = FAKE_SYNC_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.sync.sync_abstract" not in contents


def test_fake_process_manager_helper_avoids_legacy_processing_imports() -> None:
    """Require shared fake process manager helper to avoid legacy model imports."""
    contents = FAKE_PROCESS_MANAGER_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.processing.models" not in contents


def test_fake_processor_helper_avoids_legacy_processing_abstract_imports() -> None:
    """Require shared fake processor helper to avoid legacy abstract imports."""
    contents = FAKE_PROCESSOR_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.processing.file_processor_abstract" not in contents


def test_conftest_observer_patch_avoids_hardcoded_legacy_module_path() -> None:
    """Require conftest observer monkeypatch path to avoid hardcoded legacy literal."""
    contents = CONFTEST_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.app.device_watchdog_app.Observer" not in contents


def test_conftest_watchdog_app_fixture_avoids_legacy_runtime_import() -> None:
    """Require shared watchdog fixture to import DeviceWatchdogApp from dpost runtime."""
    contents = CONFTEST_PATH.read_text(encoding="utf-8")

    assert (
        "from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp"
        not in (contents)
    )


def test_legacy_source_package_is_retired() -> None:
    """Require full legacy source package retirement from `src/ipat_watchdog`."""
    assert not LEGACY_SOURCE_ROOT.exists()


def test_dpost_metrics_module_owns_metric_definitions() -> None:
    """Require canonical dpost metrics module to own metric definitions."""
    contents = DPOST_METRICS_PATH.read_text(encoding="utf-8")

    assert "from prometheus_client import REGISTRY, Counter, Gauge, Histogram" in (
        contents
    )
    assert "FILES_PROCESSED = _counter(" in contents
    assert "SESSION_DURATION = _gauge(" in contents


def test_integration_runtime_tests_avoid_legacy_watchdog_runtime_paths() -> None:
    """Require integration runtime tests to avoid legacy watchdog runtime import paths."""
    for path in INTEGRATION_RUNTIME_TEST_PATHS:
        contents = path.read_text(encoding="utf-8")
        assert (
            "from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp"
            not in contents
        )
        assert "ipat_watchdog.core.app.device_watchdog_app.Observer" not in contents
        assert "import ipat_watchdog.core.app.device_watchdog_app as app_mod" not in (
            contents
        )


def test_unit_observability_tests_avoid_legacy_package_root_import() -> None:
    """Require observability unit tests to import canonical dpost observability module."""
    contents = UNIT_OBSERVABILITY_TEST_PATH.read_text(encoding="utf-8")

    assert "from ipat_watchdog import observability" not in contents


def test_loader_plugin_unit_tests_avoid_legacy_loader_and_test_plugin_imports() -> None:
    """Require selected loader/plugin unit tests to resolve dpost plugin boundaries."""
    mapping_contents = UNIT_PC_DEVICE_MAPPING_TEST_PATH.read_text(encoding="utf-8")
    assert "from ipat_watchdog.loader import get_devices_for_pc" not in (
        mapping_contents
    )

    plugin_contents = UNIT_TEST_PLUGINS_INTEGRATION_PATH.read_text(encoding="utf-8")
    assert "from ipat_watchdog.device_plugins.test_device.plugin import" not in (
        plugin_contents
    )
    assert "from ipat_watchdog.device_plugins.test_device.settings import" not in (
        plugin_contents
    )
    assert "from ipat_watchdog.pc_plugins.test_pc.plugin import" not in (
        plugin_contents
    )
    assert "from ipat_watchdog.pc_plugins.test_pc.settings import" not in (
        plugin_contents
    )

    plugin_loader_contents = UNIT_PLUGIN_LOADER_TEST_PATH.read_text(encoding="utf-8")
    assert "from ipat_watchdog.plugin_system import PluginLoader, hookimpl" not in (
        plugin_loader_contents
    )

    plugin_logging_contents = UNIT_PLUGIN_NO_DOUBLE_LOGGING_TEST_PATH.read_text(
        encoding="utf-8"
    )
    assert "from ipat_watchdog.plugin_system import PluginLoader" not in (
        plugin_logging_contents
    )

    pc_plugins_contents = UNIT_PC_PLUGINS_TEST_PATH.read_text(encoding="utf-8")
    assert "from ipat_watchdog.loader import load_pc_plugin" not in (
        pc_plugins_contents
    )
    assert "from ipat_watchdog.core.config import PCConfig" not in (pc_plugins_contents)
    assert "from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin" not in (
        pc_plugins_contents
    )

    test_pc_contents = UNIT_TEST_PC_PLUGIN_TEST_PATH.read_text(encoding="utf-8")
    assert "from ipat_watchdog.pc_plugins.test_pc.plugin import TestPCPlugin" not in (
        test_pc_contents
    )
    assert (
        "from ipat_watchdog.pc_plugins.test_pc.settings import build_config as build_pc_config"
        not in test_pc_contents
    )

    haake_contents = UNIT_HAAKE_PC_PLUGIN_TEST_PATH.read_text(encoding="utf-8")
    assert "from ipat_watchdog.pc_plugins.haake_blb.plugin import" not in (
        haake_contents
    )
    assert "from ipat_watchdog.pc_plugins.haake_blb.settings import" not in (
        haake_contents
    )
    assert "from ipat_watchdog.plugin_system import PCPluginRegistry" not in (
        haake_contents
    )


def test_device_plugin_unit_tests_avoid_legacy_plugin_import_paths() -> None:
    """Require core device-plugin unit tests to resolve canonical dpost modules."""
    for path in DEVICE_PLUGIN_UNIT_TEST_PATHS:
        contents = path.read_text(encoding="utf-8")
        assert "from ipat_watchdog.device_plugins" not in contents
        assert "ipat_watchdog.device_plugins." not in contents

    for path in (
        PROJECT_ROOT
        / "tests"
        / "unit"
        / "device_plugins"
        / "erm_hioki"
        / "test_file_processor.py",
        PROJECT_ROOT
        / "tests"
        / "unit"
        / "device_plugins"
        / "psa_horiba"
        / "test_staging_rename_cancel.py",
        PROJECT_ROOT
        / "tests"
        / "unit"
        / "device_plugins"
        / "sem_phenomxl2"
        / "test_file_processor.py",
        PROJECT_ROOT
        / "tests"
        / "unit"
        / "device_plugins"
        / "extr_haake"
        / "test_plugin.py",
    ):
        contents = path.read_text(encoding="utf-8")
        assert "from ipat_watchdog.core." not in contents


def test_integration_tests_avoid_legacy_import_paths() -> None:
    """Require integration tests to import canonical dpost boundaries only."""
    for path in INTEGRATION_TEST_PATHS:
        contents = path.read_text(encoding="utf-8")
        assert "from ipat_watchdog" not in contents
        assert "import ipat_watchdog" not in contents


def test_core_dataflow_unit_tests_avoid_legacy_import_paths() -> None:
    """Require core data-flow unit tests to import canonical dpost boundaries."""
    for path in CORE_DATAFLOW_UNIT_TEST_PATHS:
        contents = path.read_text(encoding="utf-8")
        assert "from ipat_watchdog" not in contents
        assert "import ipat_watchdog" not in contents


def test_core_processing_and_settings_unit_tests_avoid_legacy_import_paths() -> None:
    """Require core processing/settings tests to import canonical dpost modules."""
    for path in CORE_PROCESSING_SETTINGS_UNIT_TEST_PATHS:
        contents = path.read_text(encoding="utf-8")
        assert "from ipat_watchdog" not in contents
        assert "import ipat_watchdog" not in contents


def test_remaining_test_import_sweep_avoids_legacy_import_paths() -> None:
    """Require the remaining harness/manual/UI/device tests to use dpost imports."""
    for path in REMAINING_TEST_IMPORT_SWEEP_PATHS:
        contents = path.read_text(encoding="utf-8")
        assert "from ipat_watchdog" not in contents
        assert "import ipat_watchdog" not in contents
