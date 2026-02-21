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
LEGACY_METRICS_PATH = PROJECT_ROOT / "src" / "ipat_watchdog" / "metrics.py"
UNIT_OBSERVABILITY_TEST_PATH = PROJECT_ROOT / "tests" / "unit" / "test_observability.py"
INTEGRATION_RUNTIME_TEST_PATHS = (
    PROJECT_ROOT / "tests" / "integration" / "test_integration.py",
    PROJECT_ROOT / "tests" / "integration" / "test_device_integrations.py",
    PROJECT_ROOT / "tests" / "integration" / "test_multi_processor_app_flow.py",
    PROJECT_ROOT / "tests" / "integration" / "test_extr_haake_safesave.py",
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


def test_legacy_metrics_module_reexports_dpost_metrics() -> None:
    """Require legacy metrics module to re-export canonical dpost metrics."""
    contents = LEGACY_METRICS_PATH.read_text(encoding="utf-8")

    assert "from dpost.application.metrics import (" in contents
    assert "Counter(" not in contents
    assert "Gauge(" not in contents
    assert "Histogram(" not in contents


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
