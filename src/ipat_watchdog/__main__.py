import os
import sys
import traceback
from dotenv import load_dotenv
from prometheus_client import start_http_server

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.observability import start_observability_server
from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.loader import load_device_plugin, load_pc_plugin
from ipat_watchdog.core.config.settings_store import SettingsManager, SettingsStore
from ipat_watchdog.core.config.global_settings import PCSettings
from ipat_watchdog.core.sync.sync_kadi import KadiSyncManager
from ipat_watchdog.core.ui.ui_tkinter import TKinterUI
from ipat_watchdog.core.storage.filesystem_utils import init_dirs

# Load environment variables
load_dotenv()

# Set up logger immediately (stdout JSON logging)
logger = setup_logger(__name__)

def main():
    # Load PC plugin for PC-specific settings
    pc_name = os.getenv("PC_NAME", "default_pc_blb")
    pc_plugin = load_pc_plugin(pc_name.strip())
    pc_settings = pc_plugin.get_settings()
    
    # Load all device plugins listed in DEVICE_NAMES
    device_names = os.getenv("DEVICE_NAMES", "sem_tischrem_blb").split(",")
    global_settings = PCSettings()
    
    # Collect device settings from plugins
    device_settings_list = []
    plugins = []
    for device_name in device_names:
        plugin = load_device_plugin(device_name.strip())
        device_settings = plugin.get_settings()
        device_settings_list.append(device_settings)
        plugins.append(plugin)
    
    # Initialize new settings manager and store with PC settings override
    settings_manager = SettingsManager(global_settings, device_settings_list, pc_settings)
    SettingsStore.set_manager(settings_manager)

    init_dirs()

    start_http_server(8000)
    logger.info("Prometheus metrics server started on port 8000")

    start_observability_server()
    logger.info("Observability server started on port 8001")

    ui = TKinterUI()
    sync = KadiSyncManager(ui=ui)

    # No longer need to pass a specific file processor - will be selected per file
    app = DeviceWatchdogApp(
        ui=ui,
        sync_manager=sync,
        settings_manager=settings_manager,
    )
    app.run()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Unhandled exception occurred")
        sys.exit(1)

