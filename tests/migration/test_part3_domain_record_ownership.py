"""Migration tests for Part 3 domain ownership of record entities."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_DOMAIN_RECORD_LOCAL_RECORD_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "domain" / "records" / "local_record.py"
)
DPOST_APPLICATION_RECORD_LOCAL_RECORD_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "records" / "local_record.py"
)
DPOST_APPLICATION_RECORD_MANAGER_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "records" / "record_manager.py"
)


def test_domain_local_record_module_exists() -> None:
    """Require `LocalRecord` entity ownership under domain package."""
    assert DPOST_DOMAIN_RECORD_LOCAL_RECORD_PATH.exists()


def test_application_local_record_module_is_retired() -> None:
    """Require application-level LocalRecord module retirement."""
    assert DPOST_APPLICATION_RECORD_LOCAL_RECORD_PATH.exists() is False


def test_domain_local_record_avoids_runtime_config_accessor_coupling() -> None:
    """Require domain LocalRecord to avoid direct runtime config accessors."""
    local_record_contents = DPOST_DOMAIN_RECORD_LOCAL_RECORD_PATH.read_text(
        encoding="utf-8"
    )

    assert "from dpost.application.config import current" not in local_record_contents
    assert "def _id_separator(" not in local_record_contents


def test_record_manager_imports_domain_local_record() -> None:
    """Require record manager to consume LocalRecord from domain ownership."""
    record_manager_contents = DPOST_APPLICATION_RECORD_MANAGER_PATH.read_text(
        encoding="utf-8"
    )

    assert "from dpost.domain.records.local_record import LocalRecord" in (
        record_manager_contents
    )
