import os
import sys
import queue
import time
import datetime
import shutil
from watchdog.observers import Observer

from src.config.settings import WATCH_DIR, TESTING, TESTING_PATH
from src.gui.gui_manager import UserInterface
from src.handlers.file_event_handler import FileEventHandler
from src.processing.file_processor import BaseFileProcessor
from src.sessions.session_manager import SessionManager
from src.app.logger import setup_logger

logger = setup_logger(__name__)

class DeviceWatchdogApp:
    """
    Main application class
    """
    def __init__(
            self, 
            file_processor: BaseFileProcessor,
            ui: UserInterface,
            session_manager: SessionManager,
            event_handler: FileEventHandler,
            observer,
            event_queue: queue.Queue,
        ):
        self.testing = TESTING
        self.test_path = TESTING_PATH
        self.watch_dir = WATCH_DIR

        # TODO: Add logging for testing, move respective code to storage_manager and/or up to the main
        if self.testing:             
            logger.info("Running in testing mode.")
            self._clear_watch_dir_for_testing()

        self.ui: UserInterface                  = ui
        self.session_manager: SessionManager    = session_manager
        self.file_processor: BaseFileProcessor  = file_processor
        self.event_queue: queue.Queue           = event_queue
        self.event_handler: FileEventHandler    = event_handler
        
        self.observer = observer
        self.observer.schedule(
            self.event_handler,
            path=self.watch_dir,
            recursive=False
        )
        self.observer.start()
        
        logger.info(f"Monitoring directory: {self.watch_dir}")

        self.ui.root.after(100, self.process_events)
        self.ui.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.ui.root.report_callback_exception = self.handle_exception

        self.session_manager.end_session_callback = self.end_session

        self.dict_reset_done = False

    # TODO: Add logging for testing, move respective code to storage_manager and/or up to the main
    def _clear_watch_dir_for_testing(self):
        """
        Clears the watch directory by removing all files and subdirectories.
        """
        logger.info("Clearing watch directory for testing...")
        for root, dirs, files in os.walk(self.watch_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    logger.debug(f"Removed file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to remove file '{file_path}': {e}")
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                try:
                    shutil.rmtree(dir_path)
                    logger.debug(f"Removed directory: {dir_path}")
                except Exception as e:
                    logger.error(f"Failed to remove directory '{dir_path}': {e}")

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        logger.error("An unexpected error occurred", exc_info=(exc_type, exc_value, exc_traceback))
        self.ui.show_error("Application Error", "An unexpected error occurred. Please contact the administrator.")
        self.on_closing()

    def end_session(self):
        logger.info("DeviceWatchdogApp.end_session called.")
        try:
            self.sync_records_to_database()
        except Exception as e:
            logger.exception(f"An error occurred during session end: {e}")
            self.ui.show_error("Session End Error", f"An error occurred during session end: {e}")
        finally:
            if hasattr(self.ui, 'done_dialog') and self.ui.done_dialog.winfo_exists():
                self.ui.done_dialog.destroy()
            logger.info("End session logic completed.")

    def sync_records_to_database(self):
        logger.info("Syncing files to the database...")
        self.file_processor.sync_records_to_database()

    def process_events(self):
        while not self.event_queue.empty():
            try:
                data_path, _ = self.event_queue.get_nowait()
            except queue.Empty:
                break

            logger.debug(f"Dequeued file for processing: {data_path}")
            self.file_processor.process_item(data_path)

        self.ui.root.after(100, self.process_events)

        # Handle testing logic
        if self.testing:
            self._handle_testing()
            self.testing = False

        # Daily reset at midnight
        current_time = datetime.datetime.now()
        if current_time.hour == 0 and not self.dict_reset_done:
            logger.info("End of day. Clearing daily records dict.")
            self.file_processor.clear_daily_records_dict()
            self.dict_reset_done = True

        if current_time.hour != 0:
            self.dict_reset_done = False

    def _handle_testing(self):
        """
        Handles testing by copying test files or directories to the watch directory.
        """
        if os.path.isfile(self.test_path):
            try:
                shutil.copy(self.test_path, self.watch_dir)
                logger.info(f"Copied test file from '{self.test_path}' to '{self.watch_dir}'.")
            except Exception as e:
                logger.error(f"Failed to copy test file '{self.test_path}': {e}")
        elif os.path.isdir(self.test_path):
            destination = os.path.join(self.watch_dir, os.path.basename(self.test_path))
            try:
                shutil.copytree(self.test_path, destination)
                logger.info(f"Copied test directory from '{self.test_path}' to '{destination}'.")
            except Exception as e:
                logger.error(f"Failed to copy test directory '{self.test_path}': {e}")

    def on_closing(self):
        if self.session_manager.session_active():
            self.session_manager.end_session()
        self.observer.stop()
        self.observer.join()
        self.ui.destroy()
        logger.info("Monitoring stopped.")

    def run(self):
        try:
            self.ui.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception:
            self.handle_exception(*sys.exc_info())
