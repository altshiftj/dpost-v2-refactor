import os
import logging
from watchdog.events import FileSystemEventHandler
from threading import Timer
from queue import Queue

from src.config.settings import DEBOUNCE_TIME

logger = logging.getLogger(__name__)

class FileEventHandler(FileSystemEventHandler):
    """
    Event handler that processes new files and directories with a debounce mechanism.
    Ensures items are fully written before adding them to the event queue.
    """
    def __init__(self, event_queue: Queue):
        """
        :param event_queue: Queue to place fully written file and directory paths for processing.
        """
        super().__init__()
        self.event_queue = event_queue
        self.debounce_time = DEBOUNCE_TIME
        self.timers = {}  # Maps paths to Timer objects

    def on_created(self, event):
        if event.is_directory:
            logger.info(f"Directory created: {event.src_path}")
            self._start_debounce(event.src_path, is_directory=True)
        else:
            logger.info(f"File created: {event.src_path}")
            self._start_debounce(event.src_path, is_directory=False)

    def _start_debounce(self, path: str, is_directory: bool):
        """
        Starts or resets a debounce timer for the given path.
        """
        if path in self.timers:
            self.timers[path].cancel()
            logger.debug(f"Resetting debounce timer for: {path}")

        timer = Timer(self.debounce_time, self._add_item_to_queue, args=[path, is_directory])
        self.timers[path] = timer
        timer.start()
        logger.debug(f"Started debounce timer for: {path}")

    def _add_item_to_queue(self, path: str, is_directory: bool):
        """
        Called when debounce timer expires. Adds the path to the processing queue.
        """
        if os.path.exists(path):
            logger.info(f"{'Directory' if is_directory else 'File'} ready for processing: {path}")
            self.event_queue.put((path, is_directory))
        else:
            logger.warning(f"{'Directory' if is_directory else 'File'} no longer exists: {path}")
        # Clean up the timer
        del self.timers[path]