import os
import sys
import traceback
from dotenv import load_dotenv
from prometheus_client import start_http_server

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.observability import start_observability_server
from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.loader import load_device_plugin
from ipat_watchdog.core.config.settings_store import SettingsManager
from ipat_watchdog.core.config.global_settings import GlobalSettings
from ipat_watchdog.core.sync.sync_kadi import KadiSyncManager
from ipat_watchdog.core.ui.ui_tkinter import TKinterUI
from ipat_watchdog.core.storage.filesystem_utils import init_dirs

# Load environment variables
load_dotenv()

# Set up logger immediately (stdout JSON logging)
logger = setup_logger(__name__)

def main():
    # Load all device plugins listed in DEVICE_NAMES
    device_names = os.getenv("DEVICE_NAMES", "sem_tischrem_blb").split(",")
    global_settings = GlobalSettings()
    settings_manager = SettingsManager(global_settings)
    plugins = []
    for device_name in device_names:
        plugin = load_device_plugin(device_name.strip())
        device_settings = plugin.get_settings()
        settings_manager.register_device(device_settings)
        plugins.append(plugin)

    init_dirs()

    start_http_server(8000)
    logger.info("Prometheus metrics server started on port 8000")

    start_observability_server()
    logger.info("Observability server started on port 8001")

    ui = TKinterUI()
    sync = KadiSyncManager(ui=ui)

    # For now, use the first plugin's processor for demonstration
    # Next step: update DeviceWatchdogApp to support multiple processors
    file_processor = plugins[0].get_file_processor()

    app = DeviceWatchdogApp(
        ui=ui,
        sync_manager=sync,
        file_processor=file_processor,
        settings_manager=settings_manager,
    )
    app.run()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Unhandled exception occurred")
        sys.exit(1)

