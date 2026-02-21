"""KINEXUS BLB PC plugin registration under canonical dpost namespace."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dpost.application.config import PCConfig
from dpost.pc_plugins.kinexus_blb.settings import build_config
from dpost.plugins.system import hookimpl

if TYPE_CHECKING:
    from dpost.plugins.system import PCPluginRegistry


class PCKinexusPlugin:
    """Register KINEXUS BLB workstation with canonical dpost plugin loader."""

    __test__ = False

    def __init__(self) -> None:
        self._config = build_config()

    def get_config(self) -> PCConfig:
        return self._config


@hookimpl
def register_pc_plugins(registry: "PCPluginRegistry") -> None:
    """Register canonical KINEXUS BLB PC plugin."""
    registry.register("kinexus_blb", PCKinexusPlugin)
