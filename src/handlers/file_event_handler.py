import os
import logging
from watchdog.events import FileSystemEventHandler
from threading import Timer
from queue import Queue

from src.config.settings import DEBOUNCE_TIME

logger = logging.getLogger(__name__)

class FileEventHandler(FileSystemEventHandler):
    """
    Custom event handler that processes newly created or modified paths
    (files or directories) with a debounce mechanism to ensure they are stable.
    """

    def __init__(self, event_queue: Queue):
        super().__init__()
        self.event_queue = event_queue
        self.debounce_time = DEBOUNCE_TIME
        self.timers = {}

    def on_created(self, event):
        logger.info(f"Path created: {event.src_path}")
        self._schedule_debounce(event.src_path)

    def _schedule_debounce(self, path: str):
        if path in self.timers:
            self.timers[path].cancel()
            logger.debug(f"Resetting debounce timer for: {path}")

        # Normalize case
        ext = path.lower()
        if ext.endswith('.tif') or ext.endswith('.tiff'):
            Timer(1, self._add_item_to_queue, args=[path]).start()
            logger.debug(f"Started debounce timer for: {path}")
            return

        timer = Timer(self.debounce_time, self._add_item_to_queue, args=[path])
        self.timers[path] = timer
        timer.start()
        logger.debug(f"Started/Reset debounce timer for: {path}")

    def _add_item_to_queue(self, path: str):
        if path in self.timers:
            del self.timers[path]

        ext = path.lower()
        if os.path.exists(path) and (os.path.isdir(path) or ext.endswith('.tif') or ext.endswith('.tiff')):
            logger.info(f"Path is stable and ready for processing: {path}")
            self.event_queue.put(path)
        else:
            logger.warning(f"Path no longer exists (likely removed): {path}")
