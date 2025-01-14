from src.app.logger import setup_logger
from src.app.main_app import DeviceWatchdogApp
from src.gui.user_interface import TKinterUI
from src.sessions.session_manager import SessionManager
from src.processing.file_processor import SEMFileProcessor

def main():
    logger = setup_logger(__name__)

    ui = TKinterUI()
    session_manager = SessionManager(ui.root, end_session_callback=None)

    file_processor = SEMFileProcessor(
        ui=ui,
        session_manager = session_manager)
    
    app = DeviceWatchdogApp(
        ui = ui,
        file_processor = file_processor,
        session_manager = session_manager)   

    try:
        app.run()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        logger.info("Application closed.")

if __name__ == "__main__":
    main()
