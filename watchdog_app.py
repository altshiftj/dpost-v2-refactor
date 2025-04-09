from src.app.logger import setup_logger
from src.app.main_app import DeviceWatchdogApp
from src.ui.ui_tkinter import TKinterUI
from src.sync.sync_kadi import KadiSyncManager
from src.processing.file_processor_sem import FileProcessorSEM


def main():
    logger = setup_logger(__name__)

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
