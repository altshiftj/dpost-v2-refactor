from __future__ import annotations

import datetime as dt
import threading
from pathlib import Path
from queue import Queue
from typing import Dict, Set, Tuple, Optional

from watchdog.events import FileSystemEventHandler, FileSystemEvent, DirCreatedEvent

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.config.settings_store import SettingsStore
from ipat_watchdog.core.config.settings_base import BaseSettings
from ipat_watchdog.core.storage.filesystem_utils import move_to_exception_folder

logger = setup_logger(__name__)


class FileEventHandler(FileSystemEventHandler):
    """
    Debounces single-file events and tracks “building” folders until they stabilize.

    Safeguards added:
        • graceful shutdown()  ➜ cancels timers / trackers
        • all timer callbacks wrapped in try/except
        • RLock guards _timers / _folder_trackers
        • folder-extension comparison done in lower-case
        • caps on active timers & trackers to prevent runaway threads
    """

    # ───────────────────────────── construction / teardown ────────────────────────── #

    def __init__(
        self,
        event_queue: Queue[str],
        *,
        settings: Optional[BaseSettings] = None,
        max_active_timers: int = 2_048,
        max_active_trackers: int = 128,
    ) -> None:
        super().__init__()
        self.event_queue: Queue[str] = event_queue
        self.settings: BaseSettings = settings or SettingsStore.get()

        self._timers: Dict[str, threading.Timer] = {}
        self._folder_trackers: Dict[str, FileEventHandler._FolderTracker] = {}
        self._rejected: Queue[Tuple[str, str]] = Queue()

        self._lock = threading.RLock()
        self._max_active_timers = max_active_timers
        self._max_active_trackers = max_active_trackers

    # graceful shutdown to be called by the watchdog supervisor
    def shutdown(self) -> None:
        with self._lock:
            for t in self._timers.values():
                t.cancel()
            for tr in list(self._folder_trackers.values()):
                tr._cleanup()
            self._timers.clear()
            self._folder_trackers.clear()
        logger.debug("FileEventHandler shutdown: timers & trackers cancelled")

    # ───────────────────────────────── event hook ───────────────────────────────── #

    def on_created(self, event: FileSystemEvent) -> None:  # watchdog naming (N802)
        path = Path(event.src_path)

        if self._reject_now_if_invalid_single_file(path):
            return

        if path.is_dir():
            self._start_folder_tracker(path)
        else:
            self._schedule_file_debounce(path)

    # ───────────────────────────── single-file debounce ─────────────────────────── #

    def _schedule_file_debounce(self, path: Path) -> None:
        with self._lock:
            if len(self._timers) >= self._max_active_timers:
                reason = "Debounce queue full – skipping new file"
                logger.warning("%s: %s", reason, path.name)
                self._rejected.put((str(path), reason))
                return

            path_str = str(path)
            if path_str in self._timers:
                self._timers[path_str].cancel()

            delay = (
                self.settings.FAST_DEBOUNCE_SECONDS
                if self._is_expedited_file(path)
                else self.settings.SLOW_DEBOUNCE_SECONDS
            )

            def _callback():
                try:
                    self._finalize_single_file(path_str)
                except Exception:
                    logger.exception("Unhandled error finalising file: %s", path_str)

            timer = threading.Timer(delay, _callback)
            self._timers[path_str] = timer
            logger.debug("Started %s-s debounce for file: %s", delay, path.name)
            timer.start()

    def _finalize_single_file(self, path_str: str) -> None:
        with self._lock:
            self._timers.pop(path_str, None)

        path = Path(path_str)
        if self._should_accept_file(path):
            logger.info("File stable & accepted: %s", path.name)
            self.event_queue.put(path_str)
        else:
            reason = f"Unsupported file extension '{path.suffix}'"
            logger.warning("Rejected after debounce: %s — %s", path.name, reason)
            self._rejected.put((path_str, reason))

    # ───────────────────────────── “building” folder tracker ────────────────────── #

    class _FolderTracker:
        def __init__(
            self,
            handler: "FileEventHandler",
            folder: Path,
            poll_interval: float = 1.0,
        ) -> None:
            self._h = handler
            self.folder: Path = folder
            self.last_change: dt.datetime = dt.datetime.now()
            self.last_exts: Set[str] = set()
            self._poll_interval = poll_interval

            self._timer: Optional[threading.Timer] = None
            self._schedule_next()

        # derived idle time
        @property
        def idle_seconds(self) -> float:
            return (dt.datetime.now() - self.last_change).total_seconds()

        def _schedule_next(self) -> None:
            self._timer = threading.Timer(self._poll_interval, self._safe_poll)
            self._timer.start()

        def _safe_poll(self) -> None:
            try:
                self._poll()
            except Exception:
                logger.exception("Unhandled error polling folder: %s", self.folder)
                self._cleanup()

        def _poll(self) -> None:
            if not self.folder.exists():          # tmp folder vanished
                self._cleanup()
                return

            try:
                exts = {p.suffix.lower() for p in self.folder.iterdir() if p.is_file()}
            except Exception as exc:
                self._finish_reject(f"I/O error inspecting folder: {exc}")
                return

            if exts != self.last_exts:
                self.last_exts = exts
                self.last_change = dt.datetime.now()

            required = {e.lower() for e in self._h.settings.ALLOWED_FOLDER_CONTENTS}

            # Accept
            if required.issubset(exts) and self.idle_seconds >= self._h.settings.SLOW_DEBOUNCE_SECONDS:
                logger.info("Folder stable & accepted: %s", self.folder.name)
                self._h.event_queue.put(str(self.folder))
                self._cleanup()
                return

            # Reject
            if self.idle_seconds >= self._h.settings.FOLDER_STABILITY_TIMEOUT:
                self._finish_reject("Unstable or invalid folder contents.\n"
                                    f"Moved to exceptions folder\n")
                return

            # Continue polling
            self._schedule_next()

        # helpers
        def _finish_reject(self, reason: str) -> None:
            logger.warning("Rejected folder %s — %s", self.folder.name, reason)
            move_to_exception_folder(
                str(self.folder),
                filename_prefix=self.folder.name,
                extension=""
            )
            self._h._rejected.put((str(self.folder), reason))
            self._cleanup()

        def _cleanup(self) -> None:
            if self._timer:
                self._timer.cancel()
            with self._h._lock:
                self._h._folder_trackers.pop(str(self.folder), None)

    # tracker factory with cap
    def _start_folder_tracker(self, folder: Path) -> None:
        with self._lock:
            if len(self._folder_trackers) >= self._max_active_trackers:
                reason = "Folder tracker limit reached – skipping"
                logger.warning("%s: %s", reason, folder.name)
                self._rejected.put((str(folder), reason))
                return

            path_str = str(folder)
            if path_str in self._folder_trackers:
                self._folder_trackers[path_str]._cleanup()

            self._folder_trackers[path_str] = self._FolderTracker(self, folder)
        logger.debug("Started folder tracker for: %s", folder.name)

    # ───────────────────────────── validation helpers ─────────────────────────── #

    def _reject_now_if_invalid_single_file(self, path: Path) -> bool:
        if path.is_file() and not self._should_accept_file(path):
            reason =    f"Unsupported file extension '{path.suffix}' \n" \
                        f"File moved to exceptions folder"
            
            logger.warning("Rejected immediately: %s — %s", path.name, reason)
            move_to_exception_folder(path)
            self._rejected.put((str(path), reason))
            return True
        return False

    def _should_accept_file(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in self.settings.ALLOWED_EXTENSIONS

    def _is_expedited_file(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in self.settings.EXPEDITED_EXTENSIONS

    # ───────────────────────────── public helper ─────────────────────────────── #

    def get_and_clear_rejected(self) -> list[Tuple[str, str]]:
        rejected: list[Tuple[str, str]] = []
        while not self._rejected.empty():
            rejected.append(self._rejected.get())
        return rejected
