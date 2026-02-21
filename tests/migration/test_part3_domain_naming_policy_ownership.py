"""Migration tests for Part 3 domain ownership of naming/prefix policy."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_DOMAIN_NAMING_POLICY_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "domain" / "naming" / "prefix_policy.py"
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
DPOST_APPLICATION_RENAME_FLOW_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "processing" / "rename_flow.py"
)
DPOST_HIOKI_PROCESSOR_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "device_plugins"
    / "erm_hioki"
    / "file_processor.py"
)


def test_domain_naming_policy_module_exists() -> None:
    """Require naming prefix policy ownership under the domain package."""
    assert DPOST_DOMAIN_NAMING_POLICY_PATH.exists()


def test_application_naming_policy_module_exists() -> None:
    """Require an application naming facade for config-aware policy use."""
    assert DPOST_APPLICATION_NAMING_POLICY_PATH.exists()


def test_filesystem_utils_retires_prefix_policy_functions() -> None:
    """Require infrastructure filesystem helpers to stop owning naming policy."""
    filesystem_contents = DPOST_FILESYSTEM_UTILS_PATH.read_text(encoding="utf-8")

    assert "def is_valid_prefix(" not in filesystem_contents
    assert "def sanitize_prefix(" not in filesystem_contents
    assert "def sanitize_and_validate(" not in filesystem_contents
    assert "def explain_filename_violation(" not in filesystem_contents
    assert "def analyze_user_input(" not in filesystem_contents


def test_application_processing_flows_use_application_naming_facade() -> None:
    """Require routing/rename orchestration to consume app naming policy facade."""
    routing_contents = DPOST_APPLICATION_ROUTING_PATH.read_text(encoding="utf-8")
    rename_contents = DPOST_APPLICATION_RENAME_FLOW_PATH.read_text(encoding="utf-8")

    assert (
        "from dpost.application.naming.policy import sanitize_and_validate"
        in routing_contents
    )
    assert "from dpost.application.naming.policy import (" in rename_contents


def test_hioki_processor_uses_application_naming_policy_facade() -> None:
    """Require Hioki processor to consume the app naming policy facade."""
    processor_contents = DPOST_HIOKI_PROCESSOR_PATH.read_text(encoding="utf-8")

    assert (
        "from dpost.application.naming.policy import is_valid_prefix"
        in processor_contents
    )
