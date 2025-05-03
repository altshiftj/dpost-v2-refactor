import os
import sys
import traceback
from dotenv import load_dotenv
from prometheus_client import start_http_server

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.observability import start_observability_server
from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.loader import load_device_plugin
from ipat_watchdog.core.config.settings_store import SettingsStore
from ipat_watchdog.core.sync.sync_kadi import KadiSyncManager
from ipat_watchdog.core.ui.ui_tkinter import TKinterUI
from ipat_watchdog.core.storage.filesystem_utils import init_dirs

# Load environment variables
load_dotenv()

# Set up logger immediately (stdout JSON logging)
logger = setup_logger(__name__)

def main():
    device_name = os.getenv("DEVICE_NAME", "SEM_TischREM_BLB")
    plugin = load_device_plugin(device_name)
    SettingsStore.set(plugin.get_settings())

    init_dirs()

    start_http_server(8000)
    logger.info("Prometheus metrics server started on port 8000")

    start_observability_server()
    logger.info("Observability server started on port 8001")

    ui = TKinterUI()
    sync = KadiSyncManager(ui=ui)
    file_processor = plugin.get_file_processor()

    app = DeviceWatchdogApp(
        ui=ui,
        sync_manager=sync,
        file_processor=file_processor,
    )
    app.run()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Unhandled exception occurred")
        sys.exit(1)

