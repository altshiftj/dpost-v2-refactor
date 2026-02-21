"""Migration tests for rehosting runtime app loop ownership into dpost."""

from __future__ import annotations

from pathlib import Path

from dpost.application.processing.file_process_manager import _ProcessingPipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_BOOTSTRAP_DEPENDENCIES_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "infrastructure"
    / "runtime"
    / "bootstrap_dependencies.py"
)
DPOST_RUNTIME_APP_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "application"
    / "runtime"
    / "device_watchdog_app.py"
)
DPOST_RUNTIME_DEPENDENCIES_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "application"
    / "runtime"
    / "runtime_dependencies.py"
)
DPOST_PROCESSING_MANAGER_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "application"
    / "processing"
    / "file_process_manager.py"
)
DPOST_DOMAIN_PROCESSING_MODELS_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "domain" / "processing" / "models.py"
)
DPOST_RECORD_MANAGER_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "records" / "record_manager.py"
)
DPOST_SESSION_MANAGER_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "session" / "session_manager.py"
)
DPOST_APPLICATION_CONFIG_BOUNDARY_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "config" / "__init__.py"
)
DPOST_APPLICATION_METRICS_BOUNDARY_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "metrics.py"
)
DPOST_PROCESSING_HELPER_PATHS = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "application"
    / "processing"
    / "device_resolver.py",
    PROJECT_ROOT / "src" / "dpost" / "application" / "processing" / "error_handling.py",
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "application"
    / "processing"
    / "file_processor_abstract.py",
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "application"
    / "processing"
    / "modified_event_gate.py",
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "application"
    / "processing"
    / "processor_factory.py",
    PROJECT_ROOT / "src" / "dpost" / "application" / "processing" / "record_flow.py",
    PROJECT_ROOT / "src" / "dpost" / "application" / "processing" / "record_utils.py",
    PROJECT_ROOT / "src" / "dpost" / "application" / "processing" / "rename_flow.py",
    PROJECT_ROOT / "src" / "dpost" / "application" / "processing" / "routing.py",
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "application"
    / "processing"
    / "stability_tracker.py",
)


def test_bootstrap_dependencies_no_longer_import_legacy_runtime_app_module() -> None:
    """Require bootstrap dependency wiring to use dpost runtime app module."""
    dependencies_contents = DPOST_BOOTSTRAP_DEPENDENCIES_PATH.read_text(
        encoding="utf-8"
    )

    assert "ipat_watchdog.core.app.device_watchdog_app" not in dependencies_contents


def test_dpost_runtime_app_module_exists_with_watchdog_app_class() -> None:
    """Require dpost runtime app module to define the watchdog app class."""
    runtime_app_contents = DPOST_RUNTIME_APP_PATH.read_text(encoding="utf-8")

    assert "class DeviceWatchdogApp" in runtime_app_contents


def test_dpost_runtime_app_avoids_legacy_ui_adapter_and_interaction_message_imports() -> (
    None
):
    """Require runtime app module to use dpost-owned UI/message boundaries."""
    runtime_app_contents = DPOST_RUNTIME_APP_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.ui.adapters" not in runtime_app_contents
    assert "from ipat_watchdog.core.interactions import ErrorMessages" not in (
        runtime_app_contents
    )


def test_dpost_runtime_app_avoids_legacy_sync_abstract_type_import() -> None:
    """Require runtime app module sync typing to use dpost-owned ports."""
    runtime_app_contents = DPOST_RUNTIME_APP_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.sync.sync_abstract" not in runtime_app_contents


def test_dpost_runtime_app_avoids_direct_legacy_runtime_dependency_imports() -> None:
    """Require runtime app module to isolate legacy runtime deps behind dpost modules."""
    runtime_app_contents = DPOST_RUNTIME_APP_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.config" not in runtime_app_contents
    assert "ipat_watchdog.core.processing" not in runtime_app_contents
    assert "ipat_watchdog.core.session" not in runtime_app_contents


def test_runtime_dependency_module_avoids_direct_legacy_processing_imports() -> None:
    """Require runtime dependency shim retirement after dpost processing rehost."""
    assert DPOST_RUNTIME_DEPENDENCIES_PATH.exists() is False


def test_runtime_dependency_module_avoids_direct_legacy_session_imports() -> None:
    """Require runtime app module to avoid runtime dependency shim imports."""
    runtime_app_contents = DPOST_RUNTIME_APP_PATH.read_text(encoding="utf-8")

    assert "application.runtime.runtime_dependencies" not in runtime_app_contents


def test_runtime_dependency_module_avoids_direct_legacy_config_imports() -> None:
    """Require runtime app module to resolve config from dpost-owned boundaries."""
    runtime_app_contents = DPOST_RUNTIME_APP_PATH.read_text(encoding="utf-8")

    assert "from dpost.application.config import ConfigService" in runtime_app_contents


def test_runtime_dependency_module_avoids_direct_legacy_metrics_imports() -> None:
    """Require runtime app module to resolve metrics from dpost-owned boundaries."""
    runtime_app_contents = DPOST_RUNTIME_APP_PATH.read_text(encoding="utf-8")

    assert "from dpost.application.metrics import" in runtime_app_contents


def test_dpost_processing_manager_module_exists_with_file_process_manager_class() -> (
    None
):
    """Require dpost processing module to define FileProcessManager ownership seam."""
    processing_contents = DPOST_PROCESSING_MANAGER_PATH.read_text(encoding="utf-8")

    assert "class FileProcessManager" in processing_contents


def test_dpost_processing_modules_avoid_direct_legacy_record_imports() -> None:
    """Require dpost processing paths to resolve records through dpost ownership seams."""
    processing_contents = DPOST_PROCESSING_MANAGER_PATH.read_text(encoding="utf-8")
    models_contents = DPOST_DOMAIN_PROCESSING_MODELS_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.records.record_manager" not in processing_contents
    assert "ipat_watchdog.core.records.local_record" not in processing_contents
    assert "ipat_watchdog.core.records.local_record" not in models_contents


def test_dpost_record_manager_module_exists_with_record_manager_class() -> None:
    """Require dpost records module to define RecordManager ownership seam."""
    record_manager_contents = DPOST_RECORD_MANAGER_PATH.read_text(encoding="utf-8")

    assert "class RecordManager" in record_manager_contents


def test_dpost_session_manager_module_exists_with_session_manager_class() -> None:
    """Require dpost session module to define SessionManager ownership seam."""
    session_manager_contents = DPOST_SESSION_MANAGER_PATH.read_text(encoding="utf-8")

    assert "class SessionManager" in session_manager_contents


def test_dpost_processing_and_records_modules_avoid_legacy_sync_abstract_imports() -> (
    None
):
    """Require dpost processing/record ownership seams to use dpost sync ports."""
    processing_contents = DPOST_PROCESSING_MANAGER_PATH.read_text(encoding="utf-8")
    record_manager_contents = DPOST_RECORD_MANAGER_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.sync.sync_abstract" not in processing_contents
    assert "ipat_watchdog.core.sync.sync_abstract" not in record_manager_contents


def test_dpost_processing_and_records_modules_avoid_direct_legacy_storage_imports() -> (
    None
):
    """Require dpost processing/record seams to use dpost storage boundaries."""
    processing_contents = DPOST_PROCESSING_MANAGER_PATH.read_text(encoding="utf-8")
    record_manager_contents = DPOST_RECORD_MANAGER_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.storage.filesystem_utils" not in processing_contents
    assert "ipat_watchdog.core.storage.filesystem_utils" not in record_manager_contents


def test_dpost_record_manager_module_avoids_direct_legacy_config_schema_import() -> (
    None
):
    """Require dpost record manager to resolve config types through dpost config boundary."""
    record_manager_contents = DPOST_RECORD_MANAGER_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.config.schema" not in record_manager_contents


def test_dpost_processing_manager_module_avoids_direct_legacy_interactions_imports() -> (
    None
):
    """Require dpost processing manager to use dpost interaction contracts/messages."""
    processing_contents = DPOST_PROCESSING_MANAGER_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.interactions" not in processing_contents


def test_dpost_processing_and_records_modules_avoid_direct_legacy_metrics_imports() -> (
    None
):
    """Require dpost processing/record seams to resolve metrics through dpost modules."""
    processing_contents = DPOST_PROCESSING_MANAGER_PATH.read_text(encoding="utf-8")
    record_manager_contents = DPOST_RECORD_MANAGER_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.metrics" not in processing_contents
    assert "ipat_watchdog.metrics" not in record_manager_contents


def test_dpost_processing_modules_avoid_direct_legacy_processing_imports() -> None:
    """Require dpost processing surfaces to avoid direct legacy processing imports."""
    processing_contents = DPOST_PROCESSING_MANAGER_PATH.read_text(encoding="utf-8")
    models_contents = DPOST_DOMAIN_PROCESSING_MODELS_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.processing" not in processing_contents
    assert "ipat_watchdog.core.processing" not in models_contents


def test_dpost_processing_helper_modules_exist_for_ownership_seams() -> None:
    """Require dpost processing helper modules to exist for deep-core ownership."""
    for helper_path in DPOST_PROCESSING_HELPER_PATHS:
        assert helper_path.exists()


def test_dpost_processing_pipeline_retired_prepare_request_transition_helper() -> None:
    """Require transition-only request-prep helper to be retired from dpost pipeline."""
    assert hasattr(_ProcessingPipeline, "_prepare_request") is False


def test_dpost_config_boundary_module_avoids_direct_legacy_config_imports() -> None:
    """Require dpost config boundary ownership to avoid direct legacy imports."""
    config_contents = DPOST_APPLICATION_CONFIG_BOUNDARY_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.config" not in config_contents


def test_dpost_metrics_boundary_module_avoids_direct_legacy_metrics_imports() -> None:
    """Require dpost metrics boundary ownership to avoid direct legacy imports."""
    metrics_contents = DPOST_APPLICATION_METRICS_BOUNDARY_PATH.read_text(
        encoding="utf-8"
    )

    assert "ipat_watchdog.metrics" not in metrics_contents
