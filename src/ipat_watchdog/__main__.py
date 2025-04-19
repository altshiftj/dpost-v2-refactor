from ipat_watchdog.app.logger import setup_logger
logger = setup_logger(__name__)    

import os
from dotenv import load_dotenv
from prometheus_client import start_http_server
import time

from ipat_watchdog.metrics import (
    FILES_PROCESSED,
    EXCEPTIONS_THROWN,
    SESSION_DURATION,
    FILES_PROCESSED_BY_RECORD,
    FILES_FAILED,
    EVENTS_PROCESSED,
    FILE_PROCESS_TIME,
    SESSION_EXIT_STATUS,
)

from ipat_watchdog.observability import start_observability_server
from ipat_watchdog.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.plugins.loader import load_device_plugin
from ipat_watchdog.config.settings_store import SettingsStore
from ipat_watchdog.sync.sync_kadi import KadiSyncManager
from ipat_watchdog.ui.ui_tkinter import TKinterUI
from ipat_watchdog.storage.filesystem_utils import init_dirs

load_dotenv()

def main():
    device_name = os.getenv("DEVICE_NAME", "SEM_TischREM_BLB")
    plugin = load_device_plugin(device_name)
    SettingsStore.set(plugin.get_settings())
    init_dirs()

    start_http_server(8000)  # exposes metrics on http://localhost:8000/metrics
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
    main()
