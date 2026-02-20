"""Migration tests for Phase 9 native dpost bootstrap boundaries."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_RUNTIME_BOOTSTRAP_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "runtime" / "bootstrap.py"
)
DPOST_COMPOSITION_PATH = PROJECT_ROOT / "src" / "dpost" / "runtime" / "composition.py"
LEGACY_BOOTSTRAP_MODULE_PATH = "ipat_watchdog.core.app.bootstrap"


def _read_utf8(path: Path) -> str:
    """Return UTF-8 text content for a repository file."""
    return path.read_text(encoding="utf-8")


def test_runtime_bootstrap_module_has_no_legacy_bootstrap_dependency() -> None:
    """Require runtime bootstrap boundary to avoid legacy bootstrap delegation."""
    bootstrap_contents = _read_utf8(DPOST_RUNTIME_BOOTSTRAP_PATH)

    assert LEGACY_BOOTSTRAP_MODULE_PATH not in bootstrap_contents


def test_runtime_composition_has_no_legacy_bootstrap_type_dependencies() -> None:
    """Require composition boundary to avoid legacy bootstrap type coupling."""
    composition_contents = _read_utf8(DPOST_COMPOSITION_PATH)

    assert LEGACY_BOOTSTRAP_MODULE_PATH not in composition_contents
