"""Reference dpost PC plugin used for runtime validation paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dpost.application.config import PCConfig
from dpost.pc_plugins.test_pc.settings import build_config
from dpost.plugins.system import hookimpl

if TYPE_CHECKING:
    from dpost.plugins.system import PCPluginRegistry


class TestPCPlugin:
    """Reference dpost test PC plugin for plugin-loading ownership tests."""

    __test__ = False

    def __init__(self, override_paths: dict | None = None) -> None:
        self._config = build_config(override_paths=override_paths)

    def get_config(self) -> PCConfig:
        return self._config


@hookimpl
def register_pc_plugins(registry: "PCPluginRegistry") -> None:
    """Register the reference dpost test PC plugin."""
    registry.register("test_pc", TestPCPlugin)
