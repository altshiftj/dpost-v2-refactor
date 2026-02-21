"""Migration tests for Phase 13 canonical startup legacy-retirement boundaries."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_utf8(path: Path) -> str:
    """Return UTF-8 text content for a repository file."""
    return path.read_text(encoding="utf-8")


def test_canonical_startup_modules_have_no_direct_legacy_core_imports() -> None:
    """Require canonical startup modules to avoid direct legacy core imports."""
    startup_paths = (
        PROJECT_ROOT / "src" / "dpost" / "__main__.py",
        PROJECT_ROOT / "src" / "dpost" / "runtime" / "composition.py",
        PROJECT_ROOT / "src" / "dpost" / "runtime" / "bootstrap.py",
    )

    for startup_path in startup_paths:
        assert "ipat_watchdog.core." not in _read_utf8(startup_path)


def test_canonical_main_uses_dpost_logging_adapter() -> None:
    """Require canonical startup main to resolve logging via dpost infrastructure."""
    main_contents = _read_utf8(PROJECT_ROOT / "src" / "dpost" / "__main__.py")

    assert "from dpost.infrastructure.logging import setup_logger" in main_contents


def test_runtime_bootstrap_has_no_direct_legacy_observability_import() -> None:
    """Require runtime bootstrap to resolve observability via dpost infrastructure."""
    bootstrap_contents = _read_utf8(
        PROJECT_ROOT / "src" / "dpost" / "runtime" / "bootstrap.py"
    )

    assert "from ipat_watchdog.observability import start_observability_server" not in (
        bootstrap_contents
    )


def test_dpost_logging_adapter_has_no_legacy_logging_import() -> None:
    """Require dpost logging infrastructure to own logger setup implementation."""
    logging_contents = _read_utf8(
        PROJECT_ROOT / "src" / "dpost" / "infrastructure" / "logging.py"
    )

    assert "ipat_watchdog.core.logging.logger" not in logging_contents


def test_all_dpost_source_modules_have_no_legacy_namespace_literals() -> None:
    """Require full retirement of legacy namespace usage in dpost source tree."""
    dpost_root = PROJECT_ROOT / "src" / "dpost"
    offenders: list[str] = []

    for python_path in dpost_root.rglob("*.py"):
        if "ipat_watchdog" in _read_utf8(python_path):
            offenders.append(
                str(python_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            )

    assert offenders == []
