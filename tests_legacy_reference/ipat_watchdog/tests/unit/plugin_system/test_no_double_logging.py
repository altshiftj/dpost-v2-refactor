from __future__ import annotations

import logging

from ipat_watchdog.plugin_system import PluginLoader


def test_lazy_load_device_does_not_relog_pc_registration(caplog):
    # Arrange: create a loader with lazy discovery only
    loader = PluginLoader(load_entrypoints=False, load_builtins=False)

    # Capture plugin system debug logs
    caplog.set_level(logging.DEBUG, logger="ipat_watchdog.plugin_system")

    # Act: lazily load a PC plugin, then a device plugin
    loader.load_pc("test_pc")
    loader.load_device("test_device")

    # Assert: the PC plugin registration log should appear only once
    pc_logs = [
        r for r in caplog.records if "Pc plugin 'test_pc' registered via" in r.getMessage()
    ]
    assert len(pc_logs) == 1, "PC plugin registration should not be re-logged during device lazy load"
