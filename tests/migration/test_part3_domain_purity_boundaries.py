"""Migration tests for domain-layer purity boundary hardening."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_DOMAIN_RECORD_LOCAL_RECORD_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "domain" / "records" / "local_record.py"
)
DPOST_DOMAIN_PROCESSING_MODELS_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "domain" / "processing" / "models.py"
)
DPOST_DOMAIN_PROCESSING_ROUTING_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "domain" / "processing" / "routing.py"
)


def test_domain_records_module_avoids_infrastructure_logger_dependency() -> None:
    """Require domain record entity module to avoid infrastructure imports."""
    local_record_contents = DPOST_DOMAIN_RECORD_LOCAL_RECORD_PATH.read_text(
        encoding="utf-8"
    )

    assert "from dpost.infrastructure" not in local_record_contents
    assert "setup_logger(" not in local_record_contents


def test_domain_processing_models_module_avoids_application_type_imports() -> None:
    """Require domain processing models to avoid application-layer imports."""
    models_contents = DPOST_DOMAIN_PROCESSING_MODELS_PATH.read_text(encoding="utf-8")

    assert "from dpost.application" not in models_contents


def test_domain_processing_routing_module_avoids_application_type_imports() -> None:
    """Require domain routing policy to avoid application-layer imports."""
    routing_contents = DPOST_DOMAIN_PROCESSING_ROUTING_PATH.read_text(encoding="utf-8")

    assert "from dpost.application" not in routing_contents
