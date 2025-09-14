import os
import sys
from prometheus_client import start_http_server

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.observability import start_observability_server
from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.loader import load_device_plugin, load_pc_plugin, get_devices_for_pc
from ipat_watchdog.core.config.settings_store import SettingsManager, SettingsStore
from ipat_watchdog.core.sync.sync_kadi import KadiSyncManager
from ipat_watchdog.core.ui.ui_tkinter import TKinterUI
from ipat_watchdog.core.storage.filesystem_utils import init_dirs

logger = setup_logger(__name__)

def _resolve_pc_name() -> str:
    build_pc_name = None
    try:
        from ipat_watchdog.build_config import PC_NAME as _PC_NAME  # provided by runtime hook when frozen
        build_pc_name = _PC_NAME
    except Exception:
        # Not frozen or hook didn't run — dev fallback to env
        pass

    pc = (build_pc_name or os.environ.get("PC_NAME") or "").strip()
    if not pc:
        logger.error(
            "PC_NAME not available. "
            "When frozen, ensure the PyInstaller runtime hook injects ipat_watchdog.build_config "
            "(module with PC_NAME). For dev runs, set environment variable PC_NAME."
        )
        sys.exit(1)
    return pc

def main() -> None:
    pc_name = _resolve_pc_name()
    device_names = get_devices_for_pc(pc_name)
    logger.info(f"Loading PC plugin: {pc_name} with devices: {device_names}")

    # Load PC plugin
    pc_plugin = load_pc_plugin(pc_name)
    pc_settings = pc_plugin.get_settings()

    # Collect device settings from plugins
    device_settings_list = []
    for dn in device_names:
        plugin = load_device_plugin(dn.strip())
        device_settings_list.append(plugin.get_settings())

    # Initialize settings manager
    settings_manager = SettingsManager(
        available_devices=device_settings_list,
        pc_settings=pc_settings,
    )
    SettingsStore.set_manager(settings_manager)

    init_dirs()

    # Start observability endpoints
    start_http_server(8000)
    logger.info("Prometheus metrics server started on port 8000")

    start_observability_server()
    logger.info("Observability server started on port 8001")

    # Init UI and sync manager
    ui = TKinterUI()
    sync = KadiSyncManager(ui=ui, settings_manager=settings_manager)

    # Run watchdog app
    app = DeviceWatchdogApp(
        ui=ui,
        sync_manager=sync,
        settings_manager=settings_manager,
    )
    app.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"Application failed to start: {e}")
        sys.exit(1)
