from __future__ import annotations

import datetime as dt
import time
import threading
import re
from pathlib import Path
from queue import Queue
from typing import Dict, Optional, Tuple

from watchdog.events import FileSystemEvent, FileSystemEventHandler

from ipat_watchdog.core.config.settings_base import BaseSettings
from ipat_watchdog.core.config.settings_store import SettingsStore
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.storage.filesystem_utils import move_to_exception_folder

logger = setup_logger(__name__)


class FileEventHandler(FileSystemEventHandler):
    """
    Snapshot-based watcher with:

    • N consecutive identical snapshots for stability
    • Optional sentinel file (_DONE) support
    • Temp file & temp folder filtering
    • Deferred content check – keeps polling until required files exist
    """

    def __init__(
        self,
        event_queue: Queue[str],
        *,
        settings: Optional[BaseSettings] = None,
        max_active_trackers: int = 256,
    ) -> None:
        super().__init__()
        self.event_queue = event_queue
        self.settings: BaseSettings = settings or SettingsStore.get()
        self._trackers: Dict[str, FileEventHandler._PathTracker] = {}
        self._rejected: Queue[Tuple[str, str]] = Queue()
        self._lock = threading.RLock()
        self._max_active_trackers = max_active_trackers

    def on_created(self, event: FileSystemEvent) -> None:
        path = Path(event.src_path)

        if path.is_file() and not self._is_allowed_file(path):
            self._reject_immediately(path, f"Unsupported file extension '{path.suffix}'")
            return

        if path.is_dir() and self.settings.TEMP_FOLDER_REGEX.search(path.name):
            logger.debug("Ignoring temp folder: %s", path.name)
            return

        with self._lock:
            pstr = str(path)
            if len(self._trackers) >= self._max_active_trackers:
                self._reject_immediately(path, "Tracker limit reached")
                return
            if pstr in self._trackers:
                self._trackers[pstr].stop()
            self._trackers[pstr] = self._PathTracker(self, path)

    def get_and_clear_rejected(self) -> list[Tuple[str, str]]:
        items = []
        while not self._rejected.empty():
            items.append(self._rejected.get())
        return items

    def _is_allowed_file(self, path: Path) -> bool:
        return path.suffix.lower() in self.settings.ALLOWED_EXTENSIONS

    def _reject_immediately(self, path: Path, reason: str) -> None:
        logger.warning("Rejected immediately: %s — %s", path.name, reason)
        if path.is_file():

            time.sleep(0.35)  # Wait briefly for file to be released

        move_to_exception_folder(path)
        self._rejected.put((str(path), reason))

    def shutdown(self) -> None:
        with self._lock:
            for tracker in list(self._trackers.values()):
                tracker.stop()
            self._trackers.clear()

    class _PathTracker:
        def __init__(self, handler: FileEventHandler, path: Path):
            self._h = handler
            self._settings = handler.settings
            self.path = path
            self._start = dt.datetime.now()
            self._last_metrics = self._snapshot()
            self._stable_count = 0
            self._timer: Optional[threading.Timer] = None
            self._schedule()
            logger.debug("Tracker started for %s", path.name)

        def _snapshot(self):
            if not self.path.exists():
                return None

            if self.path.is_file():
                s = self.path.stat()
                return s.st_size, s.st_mtime

            file_count = 0
            total_size = 0
            newest_mtime = 0.0
            for p in self.path.rglob("*"):
                if p.is_file() and not p.name.endswith(self._settings.TEMP_PATTERNS):
                    try:
                        s = p.stat()
                        file_count += 1
                        total_size += s.st_size
                        newest_mtime = max(newest_mtime, s.st_mtime)
                    except FileNotFoundError:
                        continue
            return file_count, total_size, newest_mtime

        def _schedule(self):
            self._timer = threading.Timer(self._settings.POLL_SECONDS, self._probe)
            self._timer.start()

        def _probe(self):
            try:
                self._check_stability()
            except Exception:
                logger.exception("Tracker crashed for %s", self.path)
                self.stop()

        def _check_stability(self):
            if not self.path.exists():
                self._reject("Path disappeared before becoming stable")
                return

            if (dt.datetime.now() - self._start).total_seconds() >= self._settings.MAX_WAIT_SECONDS:
                self._reject(f"Timeout (> {self._settings.MAX_WAIT_SECONDS}s)")
                return

            current = self._snapshot()
            if current != self._last_metrics:
                self._last_metrics = current
                self._stable_count = 0
                self._schedule()
                return

            self._stable_count += 1
            if self._stable_count < self._settings.STABLE_CYCLES:
                self._schedule()
                return

            if self.path.is_file():
                self._handle_stable_file()
            else:
                self._handle_stable_folder()

        def _handle_stable_file(self):
            if not self.path.exists():
                logger.debug("Stable file disappeared before validation: %s", self.path.name)
                self.stop()
                return

            if self._h._is_allowed_file(self.path):
                logger.info("File stable & accepted: %s", self.path.name)
                self._h.event_queue.put(str(self.path))
            else:
                self._reject(f"Unsupported file extension '{self.path.suffix}'")
            self.stop()

        def _handle_stable_folder(self):
            if not self.path.exists():
                logger.debug("Stable folder disappeared before validation: %s", self.path.name)
                self.stop()
                return

            if self._stable_count < self._settings.STABLE_CYCLES:
                self._schedule()
                return  # still stabilizing

            if self._settings.SENTINEL_NAME:
                sentinel = self.path / self._settings.SENTINEL_NAME
                if not sentinel.exists():
                    logger.debug("Waiting for sentinel %s in %s", sentinel.name, self.path.name)
                    self._schedule()
                    return

            required = {e.lower() for e in self._settings.ALLOWED_FOLDER_CONTENTS}

            # If no allowed folder contents are configured, reject the folder
            if not required:
                self._reject("Folders are not accepted for this device")
                return

            exts = {
                p.suffix.lower()
                for p in self.path.rglob("*")
                if p.is_file()
            }

            if not required.issubset(exts):
                self._reject("Missing required folder contents")
                return

            logger.info("Folder stable & accepted: %s", self.path.name)
            self._h.event_queue.put(str(self.path))
            self.stop()


        def _reject(self, reason: str):
            if not self.path.exists():
                logger.debug("Path vanished during rejection, skipping: %s", self.path.name)
                self.stop()
                return

            logger.warning("Folder/File rejected: %s — %s", self.path.name, reason)
            move_to_exception_folder(self.path)
            self._h._rejected.put((str(self.path), reason))

        def stop(self):
            if self._timer:
                self._timer.cancel()
            with self._h._lock:
                self._h._trackers.pop(str(self.path), None)


