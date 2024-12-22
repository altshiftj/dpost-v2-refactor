from src.app.logger import setup_logger
from src.config.settings import DEVICE_ID
from src.app.main_app import DeviceWatchdogApp
from src.gui.gui_manager import GUIManager
from src.sessions.session_manager import SessionManager
from src.sessions.session_controller import SessionController
from src.handlers.file_event_handler import FileEventHandler
from src.storage.path_manager import PathManager
from src.storage.storage_manager import StorageManager
from src.records.record_persistence import RecordPersistence
from src.records.record_manager import RecordManager
from src.records.id_generator import IdGenerator
from src.sync.sync_manager import SyncManager
from src.processing.file_processor import SEMFileProcessor

from watchdog.observers import Observer
from kadi_apy import KadiManager
import queue

def main():
    logger = setup_logger(__name__)

    paths = PathManager()
    persistence = RecordPersistence()
    ids = IdGenerator(DEVICE_ID)
    records = RecordManager(persistence, paths, ids)

    sync = SyncManager(db_manager=KadiManager())
    storage = StorageManager(paths)

    event_queue = queue.Queue()
    event_handler = FileEventHandler(event_queue)

    observer = Observer()

    ui = GUIManager()
    session_manager = SessionManager(ui.root, end_session_callback=None)
    session_controller = SessionController(session_manager, ui)

    file_processor = SEMFileProcessor(
        ui=ui,
        session_manager=session_manager,
        session_controller=session_controller,
        paths=paths,
        storage=storage,
        persistence=persistence,
        ids=ids,
        sync=sync,
        records=records
    )

    app = DeviceWatchdogApp(
        file_processor = file_processor,
        ui = ui,
        session_manager = session_manager,
        event_handler = event_handler,
        observer = observer,
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
