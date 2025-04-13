from core.settings_store import SettingsStore
from core.app.logger import setup_logger
from core.device_watchdog_app import DeviceWatchdogApp
from core.ui.ui_tkinter import TKinterUI
from core.sync.sync_kadi import KadiSyncManager
from settings_tischrem import TischREMSettings
from core.processing.file_processor_sem import FileProcessorSEM


def main():
    logger = setup_logger(__name__)

    device_settings = TischREMSettings()

    SettingsStore.set(device_settings)

    app = DeviceWatchdogApp(
        ui=TKinterUI(),
        sync_manager=KadiSyncManager(ui=TKinterUI()),
        file_processor=FileProcessorSEM(),
    )

    try:
        app.run()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        logger.info("Application closed.")


if __name__ == "__main__":
    main()
