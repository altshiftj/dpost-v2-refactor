import sys
from datetime import datetime
import queue
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from ipat_watchdog.metrics import(
 FILES_PROCESSED,
 SESSION_DURATION,
 EXCEPTIONS_THROWN,
 FILES_FAILED,
 EVENTS_PROCESSED,
 FILE_PROCESS_TIME,
 SESSION_EXIT_STATUS
)

from ipat_watchdog.core.config.settings_store import SettingsManager
from ipat_watchdog.core.config.constants import WATCH_DIR

from ipat_watchdog.core.ui.ui_abstract import UserInterface
from ipat_watchdog.core.ui.ui_messages import ErrorMessages
from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.session.session_manager import SessionManager
from ipat_watchdog.core.sync.sync_abstract import ISyncManager
from ipat_watchdog.core.logging.logger import setup_logger

logger = setup_logger(__name__)


class BasicFileEventHandler(FileSystemEventHandler):
    """Simple file detection handler - just queues new files/folders."""
    
    def __init__(self, event_queue: queue.Queue):
        super().__init__()
        self.event_queue = event_queue
    
    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            # For files, queue immediately
            logger.debug(f"File detected: {event.src_path}")
            self.event_queue.put(event.src_path)
        else:
            # For folders, queue immediately - let FileProcessManager handle stability
            logger.debug(f"Folder detected: {event.src_path}")
            self.event_queue.put(event.src_path)


class DeviceWatchdogApp:
    """
    Coordinates file system monitoring, file processing, UI handling,
    session control, and database synchronization.
    """

    def __init__(
        self,
        ui: UserInterface,
        sync_manager: ISyncManager,
        settings_manager: SettingsManager,
        session_manager_cls=SessionManager,
        file_process_manager_cls=FileProcessManager,
    ):
        self.start_time = datetime.now()
        logger.info(f"WatchdogApp started at {self.start_time.isoformat()}")

        self.files_processed = 0
        self.settings_manager = settings_manager
        self.ui = ui

        self.session_manager = session_manager_cls(
            ui=self.ui,
            end_session_callback=self.end_session,
        )
        self._processing_lock = threading.Lock()

        # File detection components
        self.observer = None
        self.event_handler = None
        self.event_queue = queue.Queue()

        self.file_processing = file_process_manager_cls(
            ui=self.ui,
            sync_manager=sync_manager,
            session_manager=self.session_manager,
            settings_manager=self.settings_manager,
        )

    def initialize(self):
        """Initializes the file observer and UI loop."""
        logger.info(f"Monitoring directory: {WATCH_DIR}")

        self.event_handler = BasicFileEventHandler(self.event_queue)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path=WATCH_DIR, recursive=False)
        self.observer.start()

        self._schedule_next_event_check()
        self.ui.set_close_handler(self.on_closing)
        self.ui.set_exception_handler(self.handle_exception)

    def _schedule_next_event_check(self):
        self.ui.schedule_task(100, self.process_events)

    def process_events(self):
        """Check for processed files and handle rejections."""
        try:
            src_path = self.event_queue.get_nowait()
            logger.debug(f"Processing queued item: {src_path}")
            EVENTS_PROCESSED.inc()
            
            with self._processing_lock:
                with FILE_PROCESS_TIME.time():
                    self.file_processing.process_item(src_path)
            
                self.files_processed += 1
                FILES_PROCESSED.inc()
            
        except queue.Empty:
            pass
        except Exception as e:
            logger.exception(f"Error processing file: {e}")
            FILES_FAILED.inc()

        # Handle any rejected files from processing
        rejected = self.file_processing.get_and_clear_rejected()
        for path_str, reason in rejected:
            path_name = Path(path_str).name
            FILES_FAILED.inc()
            self.ui.show_error(
                "Unsupported Input",
                f"The file or folder '{path_name}' was rejected.\n\n{reason}"
            )
        
        # Schedule next check
        self._schedule_next_event_check()

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        EXCEPTIONS_THROWN.inc()
        FILES_FAILED.inc()
        SESSION_EXIT_STATUS.set(1)
        logger.error("An unexpected error occurred", exc_info=(exc_type, exc_value, exc_traceback))
        self.ui.show_error(
            ErrorMessages.APPLICATION_ERROR,
            ErrorMessages.APPLICATION_ERROR_DETAILS,
        )
        self.on_closing()

    def end_session(self):
        logger.debug("End session called.")
        try:
            self.file_processing.sync_records_to_database()
        except Exception as e:
            logger.exception(f"An error occurred during session end: {e}")
            self.ui.show_error(
                ErrorMessages.SESSION_END_ERROR,
                ErrorMessages.SESSION_END_ERROR_DETAILS.format(error=e),
            )
        finally:
            logger.debug("End session completed.")

    def on_closing(self):
        end_time = datetime.now()
        duration = end_time - self.start_time
        SESSION_DURATION.set(duration.total_seconds())
        logger.info(f"WatchdogApp shutdown at {end_time.isoformat()} (uptime: {duration})")
        SESSION_EXIT_STATUS.set(0)

        if self.session_manager.session_active:
            self.session_manager.end_session()

        # Stop file monitoring
        if self.observer:
            self.observer.stop()
            self.observer.join()

        # Stop any stability trackers in FileProcessManager
        self.file_processing.shutdown()

        self.ui.destroy()

        logger.info(
            f"WatchdogApp shutdown at {end_time.isoformat()} "
            f"(uptime: {duration}, files processed: {self.files_processed})"
        )

    def run(self):
        self.initialize()
        try:
            self.ui.run_main_loop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception:
            self.handle_exception(*sys.exc_info())
