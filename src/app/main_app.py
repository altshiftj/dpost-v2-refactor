"""
main_app.py

This module contains the main application class, DeviceWatchdogApp, which orchestrates
the monitoring of a watch directory (using watchdog), processes file events, and manages
user sessions, testing logic, and database synchronization tasks.
"""

import sys
import queue

from watchdog.observers import Observer

from src.config.settings import WATCH_DIR
from src.ui.ui_abstract import UserInterface
from src.ui.ui_messages import ErrorMessages
from src.handlers.file_event_handler import FileEventHandler
from src.processing.file_process_manager import BaseFileProcessor, FileProcessManager
from src.sessions.session_manager import SessionManager
from src.sync.sync_abstract import ISyncManager
from src.app.logger import setup_logger

logger = setup_logger(__name__)


class DeviceWatchdogApp:
    """
    A main application class that coordinates:
      1. File system monitoring (via watchdog),
      2. File processing (through a device specific file processor),
      3. GUI interactions (with a UI manager),
      4. Session management and database synchronization,
      5. Graceful shutdown logic.
    """

    def __init__(
        self,
        ui: UserInterface,
        sync_manager: ISyncManager,
        file_processor: BaseFileProcessor,
    ):
        """
        Initializes the DeviceWatchdogApp with all necessary components.

        :param ui: A UserInterface implementation (e.g., TKinterUI).
        :param file_processor: A device specific subclass of BaseFileProcessor for handling file logic.
        """
        self.watch_dir = WATCH_DIR
        self.ui = ui
        self.event_queue = queue.Queue()  # Now an instance variable

        # Create a SessionManager which handles session state and timeouts,
        # and uses the UI for indicating session state to the user.
        self.session_manager = SessionManager(ui=self.ui, end_session_callback=None)

        self.sync_manager = sync_manager

        # Set up the file-processing manager, which handles file events
        # and interacts with the session manager for database syncs.
        self.file_processing = FileProcessManager(
            ui=self.ui,
            sync_manager=self.sync_manager,
            session_manager=self.session_manager,
            file_processor=file_processor,
        )

        self._setup_observer()

        logger.info(f"Monitoring directory: {self.watch_dir}")

        # Schedule periodic event processing.
        self.ui.schedule_task(interval_ms=1000, callback=self.process_events)

        # Set up UI handlers.
        self.ui.set_close_handler(self.on_closing)
        self.ui.set_exception_handler(self.handle_exception)

        self.session_manager.end_session_callback = self.end_session

        # Initialize the log sync counter.
        self.log_sync_counter = 0

    def _setup_observer(self):
        """Helper method to configure and start the watchdog observer."""
        event_handler = FileEventHandler(self.event_queue)
        self.directory_observer = Observer()
        self.directory_observer.schedule(
            event_handler, path=self.watch_dir, recursive=False
        )
        self.directory_observer.start()

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Handles unexpected exceptions by logging and displaying an error
        message to the user, then closes the application.
        """
        logger.error(
            "An unexpected error occurred",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        self.ui.show_error(
            ErrorMessages.APPLICATION_ERROR, ErrorMessages.APPLICATION_ERROR_DETAILS
        )
        self.on_closing()

    def end_session(self):
        """
        Callback for when a session ends (either by timeout or user action).
        Attempts to sync any records to the database, then cleans up.
        """
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
            # If there's a "Done" dialog open in the UI, close it.
            if hasattr(self.ui, "done_dialog") and self.ui.done_dialog.winfo_exists():
                self.ui.done_dialog.destroy()
            logger.debug("End session completed.")

    def process_events(self):
        """
        Periodically invoked to:
        1. Process any queued file system events from FileEventHandler.
        2. Periodically sync logs to the database.
        """
        while not self.event_queue.empty():
            try:
                data_path = self.event_queue.get_nowait()
            except queue.Empty:
                break
            logger.debug(f"Dequeued file for processing: {data_path}")
            self.file_processing.process_item(data_path)

        # Sync logs to database every 9000 iterations (~15 minutes)
        # Also, if the counter is 0 (initial iteration), sync logs.
        if self.log_sync_counter == 0 or self.log_sync_counter >= 9000:
            self.file_processing.sync_logs_to_database()
            self.log_sync_counter = 0

        # Increment for the next iteration.
        self.log_sync_counter += 1

        # Schedule the next iteration.
        self.ui.schedule_task(100, self.process_events)

    def on_closing(self):
        """
        Invoked when the user attempts to close the UI, or when a KeyboardInterrupt
        is caught. Cleans up the observer, ends the session, and destroys the UI.
        """
        if self.session_manager.session_active:
            self.session_manager.end_session()

        # Stop the observer and join the thread.
        self.directory_observer.stop()
        self.directory_observer.join()

        # Destroy the UI.
        self.ui.destroy()
        logger.info("Monitoring stopped.")

    def run(self):
        """
        Main entry point for running the UI main loop.
        Handles KeyboardInterrupt and other exceptions to gracefully shut down.
        """
        try:
            self.ui.run_main_loop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception:
            self.handle_exception(*sys.exc_info())
