"""Migration tests for Phase 8 canonical dpost identity cutover."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
README_PATH = PROJECT_ROOT / "README.md"
USER_README_PATH = PROJECT_ROOT / "USER_README.md"
DEVELOPER_README_PATH = PROJECT_ROOT / "DEVELOPER_README.md"
PIPELINE_UTILS_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "infra"
    / "windows"
    / "consolidated_pipelines"
    / "pipeline-utils.ps1"
)
PIPELINE_README_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "infra"
    / "windows"
    / "consolidated_pipelines"
    / "README.md"
)
LEGACY_MAIN_PATH = PROJECT_ROOT / "src" / "ipat_watchdog" / "__main__.py"
DPOST_MAIN_PATH = PROJECT_ROOT / "src" / "dpost" / "__main__.py"
DPOST_COMPOSITION_PATH = PROJECT_ROOT / "src" / "dpost" / "runtime" / "composition.py"
DPOST_PLUGIN_SYSTEM_PATH = PROJECT_ROOT / "src" / "dpost" / "plugins" / "system.py"


def _load_project_metadata() -> dict[str, Any]:
    """Return the `[project]` table from `pyproject.toml`."""
    with PYPROJECT_PATH.open("rb") as pyproject_file:
        pyproject_data = tomllib.load(pyproject_file)
    return pyproject_data["project"]


def _read_utf8(path: Path) -> str:
    """Return UTF-8 text content for a repository file."""
    return path.read_text(encoding="utf-8")


def test_project_name_is_canonical_dpost() -> None:
    """Require `pyproject.toml` canonical project identity to be `dpost`."""
    project_metadata = _load_project_metadata()

    assert project_metadata["name"] == "dpost"


def test_console_scripts_expose_dpost_only() -> None:
    """Require console scripts to keep `dpost` and retire `ipat-watchdog`."""
    project_metadata = _load_project_metadata()
    scripts: dict[str, str] = project_metadata.get("scripts", {})

    assert scripts.get("dpost") == "dpost.__main__:main"
    assert "ipat-watchdog" not in scripts


def test_readme_is_canonical_dpost_identity() -> None:
    """Require top-level README to stop advertising migration/legacy identity."""
    readme_contents = _read_utf8(README_PATH)
    header_line = readme_contents.splitlines()[0]

    assert header_line.strip() == "# dpost"
    assert "Migrating to dpost" not in readme_contents
    assert "Legacy: `ipat-watchdog` -> `ipat_watchdog.__main__:main`" not in (
        readme_contents
    )


def test_user_and_developer_readmes_use_dpost_startup_commands() -> None:
    """Require user/developer docs to advertise only canonical dpost startup names."""
    user_readme_contents = _read_utf8(USER_README_PATH)
    developer_readme_contents = _read_utf8(DEVELOPER_README_PATH)

    assert "python -m ipat_watchdog" not in user_readme_contents
    assert "ipat-watchdog" not in user_readme_contents
    assert "python -m dpost" in user_readme_contents

    assert "python -m ipat_watchdog" not in developer_readme_contents
    assert "console script `ipat-watchdog`" not in developer_readme_contents
    assert "python -m dpost" in developer_readme_contents


def test_windows_pipeline_scripts_do_not_hardcode_legacy_identity() -> None:
    """Require Windows deployment scripts/docs to remove hardcoded legacy namespaces."""
    pipeline_utils_contents = _read_utf8(PIPELINE_UTILS_PATH)
    pipeline_readme_contents = _read_utf8(PIPELINE_README_PATH)

    assert "entry_points(group='ipat_watchdog.pc_plugins')" not in (
        pipeline_utils_contents
    )
    assert "ipat_watchdog.pc_device_mapping" not in pipeline_readme_contents


def test_legacy_entrypoint_is_removed_post_sunset() -> None:
    """Require post-sunset retirement of the legacy compatibility entrypoint."""
    assert not LEGACY_MAIN_PATH.is_file()


def test_dpost_main_no_longer_imports_legacy_bootstrap_symbols() -> None:
    """Require dpost main entrypoint to avoid direct legacy bootstrap imports."""
    dpost_main_contents = _read_utf8(DPOST_MAIN_PATH)

    assert "from ipat_watchdog.core.app.bootstrap import" not in dpost_main_contents


def test_dpost_composition_no_longer_delegates_to_legacy_bootstrap() -> None:
    """Require dpost composition root to retire direct legacy bootstrap delegation."""
    composition_contents = _read_utf8(DPOST_COMPOSITION_PATH)

    assert "bootstrap as legacy_bootstrap" not in composition_contents
    assert "temporary implementation delegates to the existing ipat_watchdog" not in (
        composition_contents.lower()
    )


def test_plugin_install_hints_use_dpost_package_name() -> None:
    """Require plugin install guidance to use canonical dpost package naming."""
    plugin_system_contents = _read_utf8(DPOST_PLUGIN_SYSTEM_PATH)

    assert "pip install ipat-watchdog[" not in plugin_system_contents
    assert "pip install dpost[" in plugin_system_contents
