"""Migration tests for Part 3 domain ownership of batch/staging policies."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_DOMAIN_BATCH_MODELS_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "domain" / "processing" / "batch_models.py"
)
DPOST_DOMAIN_STAGING_POLICY_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "domain" / "processing" / "staging.py"
)
DPOST_APPLICATION_BATCH_MODELS_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "processing" / "batch_models.py"
)
DPOST_APPLICATION_STAGING_UTILS_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "application" / "processing" / "staging_utils.py"
)
DPOST_INFRA_STAGING_DIRS_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "infrastructure" / "storage" / "staging_dirs.py"
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


def test_domain_batch_models_module_exists() -> None:
    """Require batch value models to be owned by domain processing package."""
    assert DPOST_DOMAIN_BATCH_MODELS_PATH.exists()


def test_domain_staging_policy_module_exists() -> None:
    """Require staging reconstruction policies to be owned by domain package."""
    assert DPOST_DOMAIN_STAGING_POLICY_PATH.exists()


def test_application_batch_models_module_is_retired() -> None:
    """Require application-local batch models module retirement."""
    assert DPOST_APPLICATION_BATCH_MODELS_PATH.exists() is False


def test_application_staging_utils_module_is_retired() -> None:
    """Require application staging helper module retirement."""
    assert DPOST_APPLICATION_STAGING_UTILS_PATH.exists() is False


def test_infrastructure_staging_dirs_module_exists() -> None:
    """Require filesystem staging directory helper ownership under infrastructure."""
    assert DPOST_INFRA_STAGING_DIRS_PATH.exists()


def test_batch_processors_import_domain_owned_batch_and_staging_modules() -> None:
    """Require staged batch processors to consume domain-owned policy/value modules."""
    psa_contents = DPOST_PSA_PROCESSOR_PATH.read_text(encoding="utf-8")
    rhe_contents = DPOST_RHE_PROCESSOR_PATH.read_text(encoding="utf-8")

    assert "from dpost.domain.processing.batch_models import (" in psa_contents
    assert "from dpost.domain.processing.staging import (" in psa_contents
    assert (
        "from dpost.infrastructure.storage.staging_dirs import create_unique_stage_dir"
        in psa_contents
    )

    assert "from dpost.domain.processing.batch_models import (" in rhe_contents
    assert "from dpost.domain.processing.staging import (" in rhe_contents
    assert (
        "from dpost.infrastructure.storage.staging_dirs import create_unique_stage_dir"
        in rhe_contents
    )
