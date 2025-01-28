import os
import logging
import time
from watchdog.events import FileSystemEventHandler
from threading import Timer
from queue import Queue

from src.config.settings import DEBOUNCE_TIME

logger = logging.getLogger(__name__)

class FileEventHandler(FileSystemEventHandler):
    """
    Custom event handler that processes newly created or modified paths (files or directories)
    with a debounce mechanism to ensure they are fully written (or stable) before processing.
    """
    
    def __init__(self, event_queue: Queue):
        super().__init__()
        self.event_queue = event_queue
        self.debounce_time = DEBOUNCE_TIME
        self.timers = {}  # Maps a path to a Timer object
    
    def on_created(self, event):
        """
        Called when a file or directory is created. Starts or resets a debounce timer.
        
        :param event: The event object containing information about the creation.
        """
        logger.info(f"Path created: {event.src_path}")
        self._schedule_debounce(event.src_path)

    def _schedule_debounce(self, path: str):
        """
        Create or reset a timer for the path. If any additional changes are detected
        (i.e., more on_created/on_modified calls) before the timer fires, reset the timer.
        """
        if path in self.timers:
            self.timers[path].cancel()
            logger.debug(f"Resetting debounce timer for: {path}")

        if path.endswith('.tiff') or path.endswith('.tif'):
            Timer(1, self._add_item_to_queue, args=[path]).start()
            logger.debug(f"Started debounce timer for: {path}")
            return

        timer = Timer(self.debounce_time, self._add_item_to_queue, args=[path])
        self.timers[path] = timer
        timer.start()
        logger.debug(f"Started/Reset debounce timer for: {path}")

    def _add_item_to_queue(self, path: str):
        """
        Called when the timer expires (no changes for `debounce_time`).
        We then check if the path still exists. If yes, we enqueue it.
        """
        # Remove this timer from the dict since it's done.
        if path in self.timers:
            del self.timers[path]

        if os.path.exists(path) and (path.endswith('') or path.endswith('.tif') or path.endswith('.tiff')):
            logger.info(f"Path is stable and ready for processing: {path}")
            self.event_queue.put(path)
        else:
            logger.warning(f"Path no longer exists (likely removed): {path}")
