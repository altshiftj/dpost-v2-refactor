from ipat_watchdog.app.logger import setup_logger
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from threading import Timer
from queue import Queue

from ipat_watchdog.config.settings_store import SettingsStore
from ipat_watchdog.config.settings_base import BaseSettings

logger = setup_logger(__name__)


class FileEventHandler(FileSystemEventHandler):
    """
    Custom event handler that processes newly created or modified paths
    (files or directories) with a debounce mechanism to ensure they are stable.
    """

    def __init__(self, event_queue: Queue):
        super().__init__()
        self.event_queue = event_queue
        self.settings: BaseSettings = SettingsStore.get()
        self.timers = {}

    def on_created(self, event) -> None:
        logger.info(f"Path created: {event.src_path}")
        self._schedule_debounce(event.src_path)

    def _has_allowed_extension(self, path_obj: Path) -> bool:
        """
        Return True if the file extension is in the list of allowed extensions
        as defined in the settings.
        """
        return path_obj.suffix.lower() in self.settings.ALLOWED_EXTENSIONS

    def _should_enqueue(self, path_obj: Path) -> bool:
        """
        Determine if the path should be enqueued based solely on its existence.
        """
        return path_obj.exists()

    def _schedule_debounce(self, path: str) -> None:
        if path in self.timers:
            self.timers[path].cancel()
            logger.debug(f"Resetting debounce timer for: {path}")

        path_obj = Path(path)
        delay = 1 if self._has_allowed_extension(path_obj) else self.settings.DEBOUNCE_TIME

        timer = Timer(delay, self._add_item_to_queue, args=[path])
        self.timers[path] = timer
        logger.debug(f"Started debounce timer (delay={delay}s) for: {path}")
        timer.start()

    def _add_item_to_queue(self, path: str) -> None:
        if path in self.timers:
            del self.timers[path]

        path_obj = Path(path)
        if self._should_enqueue(path_obj):
            logger.info(f"Path is stable and ready for processing: {path}")
            self.event_queue.put(path)
        else:
            logger.warning(f"Path no longer exists (likely removed): {path}")
