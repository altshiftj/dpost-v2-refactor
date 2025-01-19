from src.app.logger import setup_logger
from src.app.main_app import DeviceWatchdogApp
from src.gui.user_interface import TKinterUI
from src.processing.file_processor import SEMFileProcessor

def main():
    logger = setup_logger(__name__)

    app = DeviceWatchdogApp(
        ui = TKinterUI(),
        file_processor = SEMFileProcessor()
        )   

    try:
        app.run()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        logger.info("Application closed.")

if __name__ == "__main__":
    main()
