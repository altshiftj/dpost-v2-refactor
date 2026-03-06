"""PyInstaller baseline support for the canonical V2 executable."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from PyInstaller.utils.hooks import collect_submodules

EXECUTABLE_NAME = "dpost-v2-headless"

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


def accepted_plugin_packages() -> tuple[str, ...]:
    """Return the accepted V2 plugin packages included in the baseline build."""
    return _ACCEPTED_PLUGIN_PACKAGES


def canonical_entry_script(repo_root: Path | str) -> Path:
    """Resolve the canonical `dpost` entry script for packaging."""
    return (Path(repo_root) / "src" / "dpost" / "__main__.py").resolve()


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
    "EXECUTABLE_NAME",
    "accepted_plugin_packages",
    "canonical_entry_script",
    "collect_hiddenimports",
]
