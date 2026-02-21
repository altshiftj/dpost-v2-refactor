"""Migration tests for Phase 6 plugin hygiene and discovery hardening."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from dpost.plugins.system import PluginLoader

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
DEVICE_PLUGIN_ROOT = PROJECT_ROOT / "src" / "dpost" / "device_plugins"
PC_PLUGIN_ROOT = PROJECT_ROOT / "src" / "dpost" / "pc_plugins"


def _plugin_directories(root: Path) -> tuple[Path, ...]:
    """Return plugin package directories, excluding dunder artifact folders."""
    return tuple(
        sorted(
            (
                path
                for path in root.iterdir()
                if path.is_dir() and not path.name.startswith("__")
            ),
            key=lambda path: path.name,
        )
    )


def _has_required_plugin_modules(package_dir: Path) -> bool:
    """Return whether a plugin package has the minimum source module set."""
    return (package_dir / "plugin.py").is_file() and (
        package_dir / "settings.py"
    ).is_file()


def _load_optional_dependency_groups() -> set[str]:
    """Load optional dependency group names from `pyproject.toml`."""
    with PYPROJECT_PATH.open("rb") as pyproject_file:
        project_data = tomllib.load(pyproject_file)
    return set(project_data["project"].get("optional-dependencies", {}))


def test_plugin_package_init_module_naming_is_normalized() -> None:
    """Require plugin packages to use `__init__.py`, not `_init_.py`."""
    invalid_package_names: list[str] = []
    for plugin_root in (DEVICE_PLUGIN_ROOT, PC_PLUGIN_ROOT):
        for package_dir in _plugin_directories(plugin_root):
            has_standard_init = (package_dir / "__init__.py").is_file()
            has_misnamed_init = (package_dir / "_init_.py").is_file()
            if not has_standard_init or has_misnamed_init:
                invalid_package_names.append(package_dir.name)

    assert invalid_package_names == []


def test_plugin_directories_contain_required_source_modules() -> None:
    """Require each plugin directory to include `plugin.py` and `settings.py`."""
    stale_package_names: list[str] = []
    for plugin_root in (DEVICE_PLUGIN_ROOT, PC_PLUGIN_ROOT):
        for package_dir in _plugin_directories(plugin_root):
            if not _has_required_plugin_modules(package_dir):
                stale_package_names.append(package_dir.name)

    assert stale_package_names == []


def test_non_test_plugin_directories_align_with_optional_dependency_groups() -> None:
    """Require non-test plugin directories to map to optional dependency groups."""
    optional_dependency_groups = _load_optional_dependency_groups()
    non_test_plugin_directories = {
        package_dir.name
        for plugin_root in (DEVICE_PLUGIN_ROOT, PC_PLUGIN_ROOT)
        for package_dir in _plugin_directories(plugin_root)
        if not package_dir.name.startswith("test_")
    }
    missing_optional_groups = sorted(
        non_test_plugin_directories - optional_dependency_groups
    )

    assert missing_optional_groups == []


def test_builtin_discovery_matches_source_plugin_inventory() -> None:
    """Require built-in discovery to expose every source plugin package."""
    loader = PluginLoader(load_entrypoints=False, load_builtins=True)
    expected_device_plugins = {
        package_dir.name
        for package_dir in _plugin_directories(DEVICE_PLUGIN_ROOT)
        if _has_required_plugin_modules(package_dir)
    }
    expected_pc_plugins = {
        package_dir.name
        for package_dir in _plugin_directories(PC_PLUGIN_ROOT)
        if _has_required_plugin_modules(package_dir)
    }

    assert set(loader.available_device_plugins()) == expected_device_plugins
    assert set(loader.available_pc_plugins()) == expected_pc_plugins


def test_unknown_device_plugin_error_lists_available_plugins() -> None:
    """Require unknown-plugin errors to include actionable available-plugin hints."""
    loader = PluginLoader(load_entrypoints=False, load_builtins=True)

    with pytest.raises(RuntimeError) as exc_info:
        loader.load_device("missing_device")

    error_message = str(exc_info.value)
    assert "missing_device" in error_message
    assert "available device plugins" in error_message.lower()
    assert "test_device" in error_message


def test_unit_mapping_tests_do_not_reference_legacy_plugin_ids() -> None:
    """Require unit plugin mapping tests to avoid stale legacy plugin IDs."""
    unit_mapping_tests = (
        PROJECT_ROOT / "tests" / "unit" / "loader" / "test_pc_device_mapping.py",
        PROJECT_ROOT / "tests" / "unit" / "pc_plugins" / "test_pc_plugins.py",
    )
    legacy_identifiers = ("twinscrew_blb", "etr_twinscrew")

    stale_references: list[str] = []
    for test_file in unit_mapping_tests:
        contents = test_file.read_text(encoding="utf-8")
        for identifier in legacy_identifiers:
            if identifier in contents:
                stale_references.append(f"{test_file.name}:{identifier}")

    assert stale_references == []
