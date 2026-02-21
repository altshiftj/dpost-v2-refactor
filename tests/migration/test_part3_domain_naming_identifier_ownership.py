"""Migration tests for Part 3 domain ownership of naming identifier policy."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_DOMAIN_NAMING_IDENTIFIERS_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "domain" / "naming" / "identifiers.py"
)
DPOST_APPLICATION_NAMING_POLICY_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "naming" / "policy.py"
)
DPOST_FILESYSTEM_UTILS_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "infrastructure"
    / "storage"
    / "filesystem_utils.py"
)
DPOST_APPLICATION_ROUTING_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "processing" / "routing.py"
)
DPOST_APPLICATION_RECORD_MANAGER_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "records" / "record_manager.py"
)
DPOST_APPLICATION_PROCESS_MANAGER_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "application"
    / "processing"
    / "file_process_manager.py"
)


def test_domain_naming_identifier_module_exists() -> None:
    """Require naming identifier policy ownership under the domain package."""
    assert DPOST_DOMAIN_NAMING_IDENTIFIERS_PATH.exists()


def test_application_naming_policy_exposes_identifier_helpers() -> None:
    """Require app naming facade to expose config-aware identifier helpers."""
    policy_contents = DPOST_APPLICATION_NAMING_POLICY_PATH.read_text(encoding="utf-8")

    assert "def parse_filename(" in policy_contents
    assert "def generate_record_id(" in policy_contents
    assert "def generate_file_id(" in policy_contents


def test_filesystem_utils_retires_identifier_policy_functions() -> None:
    """Require infrastructure filesystem helpers to retire pure naming identifiers."""
    filesystem_contents = DPOST_FILESYSTEM_UTILS_PATH.read_text(encoding="utf-8")

    assert "def parse_filename(" not in filesystem_contents
    assert "def generate_record_id(" not in filesystem_contents
    assert "def generate_file_id(" not in filesystem_contents


def test_application_routing_and_records_use_naming_policy_facade() -> None:
    """Require routing and record orchestration to consume app naming facade."""
    routing_contents = DPOST_APPLICATION_ROUTING_PATH.read_text(encoding="utf-8")
    records_contents = DPOST_APPLICATION_RECORD_MANAGER_PATH.read_text(encoding="utf-8")

    assert "from dpost.application.naming.policy import" in routing_contents
    assert "from dpost.application.naming.policy import generate_record_id" in (
        records_contents
    )


def test_processing_manager_uses_naming_policy_facade_for_parse_and_file_id() -> None:
    """Require processing manager to consume app naming facade parse/file-id helpers."""
    manager_contents = DPOST_APPLICATION_PROCESS_MANAGER_PATH.read_text(
        encoding="utf-8"
    )

    assert "from dpost.application.naming.policy import" in manager_contents
    assert "generate_file_id" in manager_contents
    assert "parse_filename" in manager_contents
