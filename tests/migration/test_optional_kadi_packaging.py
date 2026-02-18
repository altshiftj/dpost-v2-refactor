"""Migration tests for optional Kadi dependency packaging."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _load_project_metadata() -> dict[str, Any]:
    """Return the `[project]` table from `pyproject.toml`."""
    with PYPROJECT_PATH.open("rb") as pyproject_file:
        pyproject_data = tomllib.load(pyproject_file)
    return pyproject_data["project"]


def _normalize_requirement_name(requirement: str) -> str:
    """Extract and normalize a dependency name from a PEP 508 requirement."""
    normalized_name = re.split(r"[<>=!~;\\[]", requirement, maxsplit=1)[0]
    return normalized_name.strip().lower()


def test_kadi_dependency_is_optional_in_packaging() -> None:
    """Keep `kadi-apy` out of default dependencies and in an optional extra."""
    project_metadata = _load_project_metadata()
    dependencies = {
        _normalize_requirement_name(dependency)
        for dependency in project_metadata.get("dependencies", [])
    }
    optional_dependencies: dict[str, list[str]] = project_metadata.get(
        "optional-dependencies", {}
    )
    kadi_optional_dependencies = {
        _normalize_requirement_name(dependency)
        for dependency in optional_dependencies.get("kadi", [])
    }

    assert "kadi-apy" not in dependencies
    assert "kadi" in optional_dependencies
    assert "kadi-apy" in kadi_optional_dependencies
