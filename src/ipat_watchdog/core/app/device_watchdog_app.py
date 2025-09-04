import sys
from datetime import datetime
import queue
import threading
from pathlib import Path
from watchdog.observers import Observer

from ipat_watchdog.metrics import(
 FILES_PROCESSED,
 SESSION_DURATION,
 EXCEPTIONS_THROWN,
 FILES_FAILED,
 EVENTS_PROCESSED,
 FILE_PROCESS_TIME,
 SESSION_EXIT_STATUS
)

from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager

from ipat_watchdog.core.ui.ui_abstract import UserInterface
from ipat_watchdog.core.ui.ui_messages import ErrorMessages
from ipat_watchdog.core.handlers.file_event_handler import FileEventHandler
from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorBase
from ipat_watchdog.core.session.session_manager import SessionManager
from ipat_watchdog.core.sync.sync_abstract import ISyncManager
from ipat_watchdog.core.logging.logger import setup_logger

logger = setup_logger(__name__)


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
        observer_cls=Observer,
        file_event_handler_cls=FileEventHandler,
        session_manager_cls=SessionManager,
        file_process_manager_cls=FileProcessManager,
    ):
        self.start_time = datetime.now()
        logger.info(f"WatchdogApp started at {self.start_time.isoformat()}")

        self.files_processed = 0
        self.settings_manager = settings_manager
        self._processing_lock = threading.Lock()  # Ensure sequential file processing

        # Get global settings for app-level configuration
        self.global_settings = settings_manager.get_global_settings()
        self.watch_dir: Path = self.global_settings.WATCH_DIR
        self.ui = ui
        self.event_queue = queue.Queue()
        self.log_sync_counter = 0

        self.session_manager = session_manager_cls(
            ui=self.ui,
            end_session_callback=self.end_session,
        )

        self.sync_manager = sync_manager

        # Create file processing manager without specific processor
        self.file_processing = file_process_manager_cls(
            ui=self.ui,
            sync_manager=self.sync_manager,
            session_manager=self.session_manager,
        )

        self.observer_cls = observer_cls
        self.file_event_handler_cls = file_event_handler_cls
        self.directory_observer = None


    def initialize(self):
        """Initializes the file observer and UI loop."""
        self._setup_observer()

        logger.info(f"Monitoring directory: {self.watch_dir}")

        self._schedule_next_event_check()
        self.ui.set_close_handler(self.on_closing)
        self.ui.set_exception_handler(self.handle_exception)

    def _setup_observer(self):
        self.handler_instance = self.file_event_handler_cls(self.event_queue)
        observer = self.observer_cls()
        observer.schedule(self.handler_instance, path=self.watch_dir, recursive=False)
        observer.start()
        self.directory_observer = observer

    def _schedule_next_event_check(self):
        self.ui.schedule_task(100, self.process_events)

    def process_events(self):
        while not self.event_queue.empty():
            EVENTS_PROCESSED.inc()
            try:
                data_path = self.event_queue.get_nowait()
            except queue.Empty:
                break
            logger.debug(f"Dequeued file for processing: {data_path}")
            
            # Use lock to ensure only one file is processed at a time
            with self._processing_lock:
                with FILE_PROCESS_TIME.time():
                    self.file_processing.process_item(data_path)

                self.files_processed += 1
                FILES_PROCESSED.inc()      # Global Prometheus counter
        
        # Show errors for any rejected files/folders
        if self.handler_instance:
            rejected = self.handler_instance.get_and_clear_rejected()
            for path_str, reason in rejected:
                path_name = Path(path_str).name
                FILES_FAILED.inc()
                self.ui.show_error(
                    "Unsupported Input",
                    f"The file or folder '{path_name}' was rejected.\n\n{reason}"
                )
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

        if self.directory_observer:
            self.directory_observer.stop()
            self.directory_observer.join()

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
