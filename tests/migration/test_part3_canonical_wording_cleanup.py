"""Migration tests for canonical runtime wording cleanup after legacy retirement."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_KADI_ADAPTER_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "infrastructure" / "sync" / "kadi.py"
)
DPOST_PROCESS_MANAGER_PATH = (
    PROJECT_ROOT
    / "src"
    / "dpost"
    / "application"
    / "processing"
    / "file_process_manager.py"
)


def test_kadi_adapter_docstrings_do_not_reference_legacy_runtime() -> None:
    """Require Kadi adapter wording to reflect canonical dpost ownership."""
    kadi_contents = DPOST_KADI_ADAPTER_PATH.read_text(encoding="utf-8")

    assert "legacy Kadi sync manager implementation" not in kadi_contents
    assert "legacy Kadi manager" not in kadi_contents


def test_processing_manager_docstring_does_not_reference_legacy_routing() -> None:
    """Require processing manager wording to avoid stale legacy-routing terminology."""
    manager_contents = DPOST_PROCESS_MANAGER_PATH.read_text(encoding="utf-8")

    assert "legacy routing behavior" not in manager_contents
