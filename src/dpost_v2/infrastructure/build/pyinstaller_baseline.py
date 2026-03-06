"""PyInstaller baseline support for the canonical V2 executable."""

from __future__ import annotations

from dataclasses import dataclass
from os import environ
from pathlib import Path
from typing import Callable, Iterable, Mapping

from PyInstaller.utils.hooks import collect_submodules

EXECUTABLE_NAME = "dpost-v2-headless"
DEBUG_EXECUTABLE_NAME = "dpost-v2-headless-debug"
DEBUG_CONSOLE_ENV_VAR = "DPOST_PYINSTALLER_DEBUG_CONSOLE"
_TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})

_PLUGIN_NAMESPACE_PACKAGES: tuple[str, ...] = (
    "dpost_v2.plugins.devices",
    "dpost_v2.plugins.pcs",
)

_ACCEPTED_PLUGIN_PACKAGES: tuple[str, ...] = (
    "dpost_v2.plugins.devices.psa_horiba",
    "dpost_v2.plugins.devices.sem_phenomxl2",
    "dpost_v2.plugins.devices.utm_zwick",
    "dpost_v2.plugins.pcs.horiba_blb",
    "dpost_v2.plugins.pcs.tischrem_blb",
    "dpost_v2.plugins.pcs.zwick_blb",
)


@dataclass(frozen=True)
class BuildVariant:
    """Resolved packaging variant for the canonical headless executable."""

    executable_name: str
    console: bool


def accepted_plugin_packages() -> tuple[str, ...]:
    """Return the accepted V2 plugin packages included in the baseline build."""
    return _ACCEPTED_PLUGIN_PACKAGES


def canonical_entry_script(repo_root: Path | str) -> Path:
    """Resolve the canonical `dpost` entry script for packaging."""
    return (Path(repo_root) / "src" / "dpost" / "__main__.py").resolve()


def resolve_build_variant(debug_console: bool = False) -> BuildVariant:
    """Resolve the canonical executable variant for packaging."""
    if debug_console:
        return BuildVariant(executable_name=DEBUG_EXECUTABLE_NAME, console=True)
    return BuildVariant(executable_name=EXECUTABLE_NAME, console=False)


def resolve_build_variant_from_env(
    env: Mapping[str, str] | None = None,
) -> BuildVariant:
    """Resolve the packaging variant from environment settings."""
    raw_value = (env or environ).get(DEBUG_CONSOLE_ENV_VAR, "")
    debug_console = raw_value.strip().lower() in _TRUTHY_ENV_VALUES
    return resolve_build_variant(debug_console=debug_console)


def collect_hiddenimports(
    collector: Callable[[str], Iterable[str]] | None = None,
) -> tuple[str, ...]:
    """Collect hidden imports required for namespace-driven V2 plugin discovery."""
    module_collector = collector or collect_submodules
    hiddenimports = {
        "dpost",
        "dpost.__main__",
        "dpost_v2",
        "dpost_v2.__main__",
        *_PLUGIN_NAMESPACE_PACKAGES,
        *_ACCEPTED_PLUGIN_PACKAGES,
    }
    for package_name in _ACCEPTED_PLUGIN_PACKAGES:
        hiddenimports.update(module_collector(package_name))
    return tuple(sorted(hiddenimports))


__all__ = [
    "BuildVariant",
    "DEBUG_CONSOLE_ENV_VAR",
    "DEBUG_EXECUTABLE_NAME",
    "EXECUTABLE_NAME",
    "accepted_plugin_packages",
    "canonical_entry_script",
    "collect_hiddenimports",
    "resolve_build_variant",
    "resolve_build_variant_from_env",
]
