"""Migration tests for Part 3 domain ownership of processing models/policies."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_DOMAIN_PROCESSING_MODELS_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "domain" / "processing" / "models.py"
)
DPOST_DOMAIN_PROCESSING_ROUTING_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "domain" / "processing" / "routing.py"
)
DPOST_APPLICATION_PROCESSING_MODELS_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "processing" / "models.py"
)
DPOST_APPLICATION_PROCESSING_ROUTING_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "processing" / "routing.py"
)
DPOST_APPLICATION_PROCESS_MANAGER_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "application"
    / "processing"
    / "file_process_manager.py"
)


def test_domain_processing_models_module_exists() -> None:
    """Require processing value models to be owned under domain package."""
    assert DPOST_DOMAIN_PROCESSING_MODELS_PATH.exists()


def test_application_processing_models_module_is_retired() -> None:
    """Require application-level processing model module retirement."""
    assert DPOST_APPLICATION_PROCESSING_MODELS_PATH.exists() is False


def test_domain_processing_routing_module_exists() -> None:
    """Require pure routing decision policy ownership under domain package."""
    assert DPOST_DOMAIN_PROCESSING_ROUTING_PATH.exists()


def test_application_routing_retires_local_policy_function() -> None:
    """Require application routing to keep only lookup helpers, not policy logic."""
    routing_contents = DPOST_APPLICATION_PROCESSING_ROUTING_PATH.read_text(
        encoding="utf-8"
    )

    assert "def fetch_record_for_prefix(" in routing_contents
    assert "def determine_routing_state(" not in routing_contents


def test_processing_manager_imports_domain_models_and_routing_policy() -> None:
    """Require processing manager to consume domain-owned model/policy modules."""
    manager_contents = DPOST_APPLICATION_PROCESS_MANAGER_PATH.read_text(
        encoding="utf-8"
    )

    assert "from dpost.domain.processing.models import (" in manager_contents
    assert (
        "from dpost.domain.processing.routing import determine_routing_decision"
        in manager_contents
    )
