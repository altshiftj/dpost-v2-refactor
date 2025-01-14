from src.app.logger import setup_logger
from src.app.main_app import DeviceWatchdogApp
from src.gui.user_interface import TKinterUI
from src.sessions.session_manager import SessionManager
from src.sessions.session_controller import SessionController
from src.handlers.file_event_handler import FileEventHandler
from src.records.record_manager import RecordManager
from src.sync.sync_manager import SyncManager
from src.processing.file_processor import SEMFileProcessor

from watchdog.observers import Observer
from kadi_apy import KadiManager
import queue

def main():
    logger = setup_logger(__name__)

    ui = TKinterUI()

    sync = SyncManager(db_manager=KadiManager(), ui=ui)
    records = RecordManager(sync)
    event_queue = queue.Queue()
    event_handler = FileEventHandler(event_queue)
    observer = Observer()

    session_manager = SessionManager(ui.root, end_session_callback=None)
    session_controller = SessionController(session_manager, ui)

    file_processor = SEMFileProcessor(
        ui=ui,
        session_controller=session_controller,
        records=records
    )

    app = DeviceWatchdogApp(
        file_processor = file_processor,
        ui = ui,
        session_manager = session_manager,
        event_handler = event_handler,
        directory_observer = observer,
        event_queue = event_queue,
    )   

    try:
        app.run()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        logger.info("Application closed.")

if __name__ == "__main__":
    main()
