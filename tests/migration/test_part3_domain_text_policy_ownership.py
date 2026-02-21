"""Migration tests for Part 3 domain ownership of text decode policy."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_DOMAIN_TEXT_POLICY_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "domain" / "processing" / "text.py"
)
DPOST_APPLICATION_TEXT_UTILS_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "processing" / "text_utils.py"
)
DPOST_PSA_PROCESSOR_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "device_plugins"
    / "psa_horiba"
    / "file_processor.py"
)
DPOST_RHE_PROCESSOR_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "device_plugins"
    / "rhe_kinexus"
    / "file_processor.py"
)
DPOST_DSV_PROCESSOR_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "device_plugins"
    / "dsv_horiba"
    / "file_processor.py"
)


def test_domain_text_policy_module_exists() -> None:
    """Require text decode policy ownership under domain package."""
    assert DPOST_DOMAIN_TEXT_POLICY_PATH.exists()


def test_application_text_utils_module_is_retired() -> None:
    """Require application-local text helper retirement."""
    assert DPOST_APPLICATION_TEXT_UTILS_PATH.exists() is False


def test_psa_and_rhe_processors_import_domain_text_policy_helper() -> None:
    """Require staged processors to consume domain-owned text decode policy helper."""
    psa_contents = DPOST_PSA_PROCESSOR_PATH.read_text(encoding="utf-8")
    rhe_contents = DPOST_RHE_PROCESSOR_PATH.read_text(encoding="utf-8")

    assert "from dpost.domain.processing.text import read_text_prefix" in psa_contents
    assert "from dpost.domain.processing.text import read_text_prefix" in rhe_contents


def test_dsv_processor_reuses_domain_text_policy_helper() -> None:
    """Require DSV processor to share domain text decode policy helper."""
    dsv_contents = DPOST_DSV_PROCESSOR_PATH.read_text(encoding="utf-8")

    assert "from dpost.domain.processing.text import read_text_prefix" in dsv_contents
    assert "def _read_text_prefix(" not in dsv_contents
