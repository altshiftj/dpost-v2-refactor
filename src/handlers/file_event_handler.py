# src/handlers/file_event_handler.py

import os
import logging
from watchdog.events import FileSystemEventHandler
from threading import Timer
from queue import Queue

from src.config.settings import DEBOUNCE_TIME

logger = logging.getLogger(__name__)

class FileEventHandler(FileSystemEventHandler):
    """
    Event handler that processes new files with a debounce mechanism.
    Ensures files are fully written before adding them to the event queue.
    """
    def __init__(self, event_queue: Queue):
        """
        :param event_queue: Queue to place fully written file paths for processing.
        :param debounce_time: Time in seconds to wait after the last modification event.
        """
        super().__init__()
        self.event_queue = event_queue
        self.debounce_time = DEBOUNCE_TIME
        self.timers = {}  # Maps file paths to Timer objects

    def on_created(self, event):
        if not event.is_directory:
            logger.info(f"File created: {event.src_path}")
            self._start_debounce(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            logger.info(f"File modified: {event.src_path}")
            self._start_debounce(event.src_path)

    def _start_debounce(self, file_path: str):
        """
        Starts or resets a debounce timer for the given file path.
        """
        if file_path in self.timers:
            self.timers[file_path].cancel()
            logger.debug(f"Resetting debounce timer for: {file_path}")

        timer = Timer(self.debounce_time, self._process_file, args=[file_path])
        self.timers[file_path] = timer
        timer.start()
        logger.debug(f"Started debounce timer for: {file_path}")

    def _process_file(self, file_path: str):
        """
        Called when debounce timer expires. Adds the file to the processing queue.
        """
        if os.path.exists(file_path):
            logger.info(f"File ready for processing: {file_path}")
            self.event_queue.put(file_path)
        else:
            logger.warning(f"File no longer exists: {file_path}")
        # Clean up the timer
        del self.timers[file_path]
