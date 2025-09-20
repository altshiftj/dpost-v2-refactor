"""Test-only PC plugin to help exercise the configuration plumbing."""

from __future__ import annotations

from typing import Optional

from ipat_watchdog.pc_plugins.pc_plugin import PCPlugin
from ipat_watchdog.pc_plugins.test_pc.settings import build_config
from ipat_watchdog.core.config import PCConfig


class TestPCPlugin(PCPlugin):
    """Test PC plugin for isolated testing."""

    def __init__(self, override_paths: Optional[dict] = None):
        self._config = build_config(override_paths=override_paths)

    def get_config(self) -> PCConfig:
        return self._config
