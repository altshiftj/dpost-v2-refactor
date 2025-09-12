import os
import sys
import traceback
from dotenv import load_dotenv
from prometheus_client import start_http_server

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.observability import start_observability_server
from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.loader import load_device_plugin, load_pc_plugin, get_devices_for_pc
from ipat_watchdog.core.config.settings_store import SettingsManager, SettingsStore
from ipat_watchdog.core.sync.sync_kadi import KadiSyncManager
from ipat_watchdog.core.ui.ui_tkinter import TKinterUI
from ipat_watchdog.core.storage.filesystem_utils import init_dirs

# Load environment variables
load_dotenv()

# Set up logger immediately (stdout JSON logging)
logger = setup_logger(__name__)

def main():
    # Get PC name and lookup device list from pyproject.toml
    pc_name = os.getenv("PC_NAME")
    if not pc_name:
        # Development fallback - set your desired PC name here
        pc_name = "tischrem_blb"
        logger.info(f"PC_NAME not set, using development fallback: {pc_name}")
    pc_name = pc_name.strip()
    device_names = get_devices_for_pc(pc_name)
    
    logger.info(f"Loading PC plugin: {pc_name} with devices: {device_names}")
    
    # Load PC plugin for PC-specific settings
    pc_plugin = load_pc_plugin(pc_name)
    pc_settings = pc_plugin.get_settings()
    
    # Collect device settings from plugins
    device_settings_list = []
    for device_name in device_names:
        plugin = load_device_plugin(device_name.strip())
        device_settings = plugin.get_settings()
        device_settings_list.append(device_settings)
    
    # Initialize settings manager
    settings_manager = SettingsManager(
        available_devices=device_settings_list,
        pc_settings=pc_settings
    )
    SettingsStore.set_manager(settings_manager)

    init_dirs()

    start_http_server(8000)
    logger.info("Prometheus metrics server started on port 8000")

    start_observability_server()
    logger.info("Observability server started on port 8001")

    ui = TKinterUI()
    
    sync = KadiSyncManager(ui=ui, settings_manager=settings_manager)

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

