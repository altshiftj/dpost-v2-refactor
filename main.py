from src.config.settings import (
    WATCH_DIR, DEVICE_NAME, RENAME_DIR, STAGING_DIR, 
    ARCHIVE_DIR, EXCEPTIONS_DIR, ARCHIVED_FILES_JSON
)
from src.app.main_app import DeviceWatchdogApp
from src.app.logger import setup_logger

logger = setup_logger(__name__)

if __name__ == "__main__":
    testing = True
    test_path = ""

    app = DeviceWatchdogApp(
        watch_dir=WATCH_DIR,
        test_path=test_path,
        session_timeout=300,
        testing=testing,
    )
    try:
        app.run()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        logger.info("Application closed.")
