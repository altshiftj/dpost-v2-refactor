import os
import sys
import queue
import time
import datetime
import shutil
from watchdog.observers import Observer

from src.config.settings import WATCH_DIR, TESTING, TESTING_PATH
from src.gui.gui_manager import GUIManager
from src.handlers.file_event_handler import FileEventHandler
from src.processing.file_processor import FileProcessor
from src.sessions.session_manager import SessionManager
from src.app.logger import setup_logger

logger = setup_logger(__name__)

class DeviceWatchdogApp:
    """
    Main application class
    """
    def __init__(self):
        self.testing = TESTING
        self.test_path = TESTING
        self.watch_dir = WATCH_DIR

        if self.testing: # Add logging for testing, move respective code to storage_manager
            for root, dirs, files in os.walk(self.watch_dir):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    shutil.rmtree(os.path.join(root, dir))

        self.ui = GUIManager()
        self.session_manager = SessionManager(
            root=self.ui.root, 
            end_session_callback=self.end_session
        )

        self.file_processor: FileProcessor = FileProcessor(
            ui=self.ui,
            session_manager=self.session_manager
        )

        self.event_queue = queue.Queue()
        self.session_timer = None

        self.event_handler = FileEventHandler(self.event_queue)
        
        self.observer = Observer()
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

            # wait for file/folder to be fully written
            # May need to be more dynamic in the future
            time.sleep(0.5)

            data_path = self.event_queue.get()
            self.file_processor.process_incoming_path(data_path)
        self.ui.root.after(100, self.process_events)

        if self.testing:
            if os.path.isfile(self.test_path):
                shutil.copy(self.test_path, self.watch_dir)
            elif os.path.isdir(self.test_path):
                shutil.copytree(self.test_path, os.path.join(self.watch_dir, os.path.basename(self.test_path)))
            self.testing = False

        if datetime.datetime.now().hour == 0:
            self.file_processor.clear_daily_records_dict()

    def on_closing(self):
        if self.session_timer:
            self.session_timer.cancel()
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
