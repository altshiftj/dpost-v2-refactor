"""Zwick BLB PC plugin registration under canonical dpost namespace."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dpost.application.config import PCConfig
from dpost.pc_plugins.zwick_blb.settings import build_config
from dpost.plugins.system import hookimpl

if TYPE_CHECKING:
    from dpost.plugins.system import PCPluginRegistry


class PCZwickPlugin:
    """Lab workstation PC plugin with canonical dpost ownership."""

    __test__ = False

    def __init__(self) -> None:
        self._config = build_config()

    def get_config(self) -> PCConfig:
        return self._config


@hookimpl
def register_pc_plugins(registry: "PCPluginRegistry") -> None:
    """Register canonical Zwick BLB PC plugin."""
    registry.register("zwick_blb", PCZwickPlugin)
