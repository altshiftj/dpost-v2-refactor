"""
device_watchdog_app.py

This module contains the main application class, DeviceWatchdogApp, which orchestrates
the monitoring of a watch directory (using watchdog), processes file events, and manages
user sessions, testing logic, and database synchronization tasks.
"""

import sys
import queue

from watchdog.observers import Observer

from src.config.settings import WATCH_DIR
from src.gui.user_interface import TKinterUI 
from src.handlers.file_event_handler import FileEventHandler
from src.processing.file_process_manager import BaseFileProcessor, FileProcessManager
from src.sessions.session_manager import SessionManager
from src.app.logger import setup_logger
from src.utils.helpers import track_function_calls

logger = setup_logger(__name__)

@track_function_calls
class DeviceWatchdogApp:
    """
    A main application class that coordinates:
      1. File system monitoring (via watchdog),
      2. File processing (through a file processor),
      3. GUI interactions (with a UI manager),
      4. Session management and database synchronization,
      5. Graceful shutdown logic.
    """

    # this is kinda a class attribute/constants
    event_queue = queue.Queue()

    def __init__(
            self,
            ui:                 TKinterUI,
            file_processor:     BaseFileProcessor
        ):
        """
        Initializes the DeviceWatchdogApp with all necessary components.

        :param file_processor: An instance of a BaseFileProcessor (or subclass) for handling file logic.
        :param ui: A UserInterface or subclass responsible for GUI interactions and dialogs.
        :param session_manager: A SessionManager that manages user sessions and timeouts.
        :param event_handler: A FileEventHandler that listens for file system events.
        :param observer: The watchdog Observer that monitors the specified directory for file changes.
        :param event_queue: A queue.Queue object where the event handler places files for processing.
        """
        self.watch_dir = WATCH_DIR      # The main directory being monitored for file changes

        # Store references to core components
        self.ui : TKinterUI = ui

        self.session_manager = SessionManager(
            ui.root,
            end_session_callback=None)
        
        self.file_processing = FileProcessManager(
            ui = ui,
            session_manager = self.session_manager,
            file_processor = file_processor)
        
        ########################################################################
        # DIRECTORY OBSERVER
        # Configure the watchdog observer to watch the directory and start observing
        event_handler = FileEventHandler(self.event_queue)
        self.directory_observer = Observer()
        self.directory_observer.schedule(
            event_handler,
            path=self.watch_dir,
            recursive=False
        )
        self.directory_observer.start()
        ########################################################################

        logger.info(f"Monitoring directory: {self.watch_dir}")

        # Periodically check for new events
        self.ui.root.after(100, self.process_events)

        # Set the GUI to handle window close and unhandled exceptions
        self.ui.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.ui.root.report_callback_exception = self.handle_exception

        # When the session manager ends a session, call self.end_session
        self.session_manager.end_session_callback = self.end_session

        self.log_sync_counter = 0

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Handles unexpected exceptions by logging and displaying an error
        message to the user, then closes the application.
        
        :param exc_type: Exception class/type.
        :param exc_value: The exception instance.
        :param exc_traceback: The traceback object with call-stack information.
        """
        logger.error("An unexpected error occurred", exc_info=(exc_type, exc_value, exc_traceback))
        self.ui.show_error("Application Error", "An unexpected error occurred. Please contact the administrator.")
        self.on_closing()

    def end_session(self):
        """
        Callback for when a session ends (either by timeout or user action).
        Attempts to sync any records to the database, then cleans up.
        """
        logger.debug("End session called.")
        try:
            self.file_processing.sync_records_to_database()
            # self.file_processing.sync_logs_to_database()
        except Exception as e:
            logger.exception(f"An error occurred during session end: {e}")
            self.ui.show_error("Session End Error", f"An error occurred during session end: {e}")
        finally:
            # If there's a "Done" dialog open, destroy it
            if hasattr(self.ui, 'done_dialog') and self.ui.done_dialog.winfo_exists():
                self.ui.done_dialog.destroy()
            logger.debug("End session completed.")

    def process_events(self):
        """
        Periodically invoked to:
          1. Process any queued file system events (placed by the FileEventHandler).
          2. Handle testing logic if enabled.
        """
        # Handle all items currently queued
        while not self.event_queue.empty():
            try:
                data_path = self.event_queue.get_nowait()
            except queue.Empty:
                break
            logger.debug(f"Dequeued file for processing: {data_path}")
            self.file_processing.process_item(data_path)

        # Sync logs to database every 9000 iterations (9000 * 100ms = 900s, 15 minutes)
        if self.log_sync_counter >= 9000 or self.log_sync_counter == 0:
            # self.file_processing.sync_logs_to_database()
            self.log_sync_counter = 0

        # periodically sync logs to database
        self.log_sync_counter += 1

        # Schedule the next iteration of this loop
        self.ui.root.after(100, self.process_events)


    def on_closing(self):
        """
        Invoked when the user attempts to close the GUI window or when the system
        catches a KeyboardInterrupt. Cleans up the observer, ends the session if 
        active, and destroys the UI.
        """
        # End the session if it's active
        if self.session_manager.session_active:
            self.session_manager.end_session()

        ########################################################################
        # Stop and join the watchdog observer
        self.directory_observer.stop()
        self.directory_observer.join()
        ########################################################################

        # Finally, destroy the GUI
        self.ui.destroy()
        logger.info("Monitoring stopped.")

    def run(self):
        """
        Main entry point for running the Tkinter main loop. 
        Includes handling of KeyboardInterrupt and other exceptions to gracefully shut down.
        """
        try:
            self.ui.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception:
            self.handle_exception(*sys.exc_info())
