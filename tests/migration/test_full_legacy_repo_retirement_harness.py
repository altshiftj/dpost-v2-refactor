"""Migration guards for legacy-retirement progress in shared test harness files."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FAKE_UI_PATH = PROJECT_ROOT / "tests" / "helpers" / "fake_ui.py"
FAKE_SYNC_PATH = PROJECT_ROOT / "tests" / "helpers" / "fake_sync.py"


def test_fake_ui_helper_avoids_legacy_interaction_imports() -> None:
    """Require shared headless UI test helper to avoid legacy interaction imports."""
    contents = FAKE_UI_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.interactions" not in contents


def test_fake_sync_helper_avoids_legacy_sync_imports() -> None:
    """Require shared sync test helper to avoid legacy sync abstract imports."""
    contents = FAKE_SYNC_PATH.read_text(encoding="utf-8")

    assert "ipat_watchdog.core.sync.sync_abstract" not in contents
