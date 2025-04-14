from core.settings_store import SettingsStore
from settings_tischrem import TischREMSettings
from core.app.logger import setup_logger
from core.device_watchdog_app import DeviceWatchdogApp
from core.ui.ui_tkinter import TKinterUI
from core.sync.sync_kadi import KadiSyncManager
from file_processor_tischrem import FileProcessorTischREM


def main():
    device_settings = TischREMSettings()
    SettingsStore.set(device_settings)
    logger = setup_logger(__name__)

    app = DeviceWatchdogApp(
        ui=TKinterUI(),
        sync_manager=KadiSyncManager(ui=TKinterUI()),
        file_processor=FileProcessorTischREM(),
    )

    try:
        app.run()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        logger.info("Application closed.")


if __name__ == "__main__":
    main()
