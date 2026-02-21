"""Migration tests for portability of manual helper scripts."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANUAL_PLUGIN_IMPORT_PATH = PROJECT_ROOT / "tests" / "manual" / "test_plugin_import.py"


def test_manual_plugin_import_script_avoids_non_ascii_console_markers() -> None:
    """Keep manual script output portable across default Windows console encodings."""
    script_contents = MANUAL_PLUGIN_IMPORT_PATH.read_text(encoding="utf-8")

    assert "✓" not in script_contents
    assert "✗" not in script_contents
