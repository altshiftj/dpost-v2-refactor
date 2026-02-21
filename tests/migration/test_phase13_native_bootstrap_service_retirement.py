"""Migration tests for retiring transition bootstrap delegation adapters."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_RUNTIME_BOOTSTRAP_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "runtime" / "bootstrap.py"
)
LEGACY_BOOTSTRAP_ADAPTER_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "infrastructure"
    / "runtime"
    / "legacy_bootstrap_adapter.py"
)


def test_runtime_bootstrap_module_has_no_legacy_bootstrap_adapter_dependency() -> None:
    """Require native runtime bootstrap to avoid transition adapter delegation."""
    bootstrap_contents = DPOST_RUNTIME_BOOTSTRAP_PATH.read_text(encoding="utf-8")

    assert "legacy_bootstrap_adapter" not in bootstrap_contents


def test_legacy_bootstrap_adapter_module_is_retired() -> None:
    """Require transition bootstrap adapter module to be retired after rehost."""
    assert LEGACY_BOOTSTRAP_ADAPTER_PATH.exists() is False
