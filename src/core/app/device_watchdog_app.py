import sys
import queue
from pathlib import Path
from watchdog.observers import Observer

from src.core.config.settings_store import SettingsStore
from src.core.config.settings_base import BaseSettings

from src.core.ui.ui_abstract import UserInterface
from src.core.ui.ui_messages import ErrorMessages
from src.core.handlers.file_event_handler import FileEventHandler
from src.core.processing.file_process_manager import FileProcessorABS, FileProcessManager
from src.core.sessions.session_manager import SessionManager
from src.core.sync.sync_abstract import ISyncManager
from src.core.app.logger import setup_logger

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
        file_processor: FileProcessorABS,
    ):
        self.settings: BaseSettings = SettingsStore.get()
        self.watch_dir: Path = self.settings.WATCH_DIR
        self.ui = ui
        self.event_queue = queue.Queue()

        self.session_manager = SessionManager(
            ui=self.ui,
            end_session_callback=self.end_session,
        )

        self.sync_manager = sync_manager

        self.file_processing = FileProcessManager(
            ui=self.ui,
            sync_manager=self.sync_manager,
            session_manager=self.session_manager,
            file_processor=file_processor,
        )

        self._setup_observer()

        logger.info(f"Monitoring directory: {self.watch_dir}")

        self.ui.schedule_task(interval_ms=1000, callback=self.process_events)
        self.ui.set_close_handler(self.on_closing)
        self.ui.set_exception_handler(self.handle_exception)

        self.log_sync_counter = 0

    def _setup_observer(self):
        handler = FileEventHandler(self.event_queue)
        self.directory_observer = Observer()
        self.directory_observer.schedule(
            handler, path=self.watch_dir, recursive=False
        )
        self.directory_observer.start()

    def handle_exception(self, exc_type, exc_value, exc_traceback):
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
            self.file_processing.sync_logs_to_database()
        except Exception as e:
            logger.exception(f"An error occurred during session end: {e}")
            self.ui.show_error(
                ErrorMessages.SESSION_END_ERROR,
                ErrorMessages.SESSION_END_ERROR_DETAILS.format(error=e),
            )
        finally:
            logger.debug("End session completed.")

    def process_events(self):
        while not self.event_queue.empty():
            try:
                data_path = self.event_queue.get_nowait()
            except queue.Empty:
                break
            logger.debug(f"Dequeued file for processing: {data_path}")
            self.file_processing.process_item(data_path)

        if self.log_sync_counter == 0 or self.log_sync_counter >= 9000:
            self.file_processing.sync_logs_to_database()
            self.log_sync_counter = 0

        self.log_sync_counter += 1
        self.ui.schedule_task(100, self.process_events)

    def on_closing(self):
        if self.session_manager.session_active:
            self.session_manager.end_session()

        self.directory_observer.stop()
        self.directory_observer.join()

        self.ui.destroy()
        logger.info("Monitoring stopped.")

    def run(self):
        try:
            self.ui.run_main_loop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception:
            self.handle_exception(*sys.exc_info())
