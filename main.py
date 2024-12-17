from src.app.main_app import DeviceWatchdogApp
from src.app.logger import setup_logger

logger = setup_logger(__name__)

if __name__ == "__main__":
    app = DeviceWatchdogApp()
    try:
        app.run()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        logger.info("Application closed.")
