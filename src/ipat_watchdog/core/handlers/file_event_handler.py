from __future__ import annotations

import datetime as dt
import threading
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
    “Version 4” – stability driven by a single periodic snapshot.

    ▸ A new file/folder starts a _PathTracker.
    ▸ Every POLL_SECONDS the tracker compares a fresh snapshot with the previous one.
    ▸ If identical → stable → validate & enqueue (or reject).
    ▸ If different  → reschedule the same timer and keep watching.
    ▸ Optional MAX_WAIT_SECONDS is a hard cap to avoid tracking pathological inputs
      that never become stable.
    """

    # --- sensible defaults (all overridable in Settings) ----------------------
    POLL_SECONDS = 0.5         # period between successive snapshots
    MAX_WAIT_SECONDS = 12.0    # hard timeout before forced rejection

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

    # ---------------------------------------------------------------- file-system
    def on_created(self, event: FileSystemEvent) -> None:  # noqa: N802
        path = Path(event.src_path)

        # quick reject for obviously unsupported single files
        if path.is_file() and not self._is_allowed_file(path):
            reason = f"Unsupported file extension '{path.suffix}'"
            self._reject_immediately(path, reason)
            return

        # start / restart a tracker
        with self._lock:
            pstr = str(path)
            if len(self._trackers) >= self._max_active_trackers:
                self._reject_immediately(path, "Tracker limit reached")
                return

            if pstr in self._trackers:  # path recreated?
                self._trackers[pstr].stop()
            self._trackers[pstr] = self._PathTracker(self, path)

    # ---------------------------------------------------------------- rejected-log
    def get_and_clear_rejected(self) -> list[Tuple[str, str]]:
        items = []
        while not self._rejected.empty():
            items.append(self._rejected.get())
        return items

    # ---------------------------------------------------------------- utilities
    def _is_allowed_file(self, path: Path) -> bool:
        return path.suffix.lower() in self.settings.ALLOWED_EXTENSIONS

    def _reject_immediately(self, path: Path, reason: str) -> None:
        logger.warning("Rejected immediately: %s — %s", path.name, reason)
        move_to_exception_folder(path)
        self._rejected.put((str(path), reason))

    # ---------------------------------------------------------------- cleanup
    def shutdown(self) -> None:
        """Stop all active trackers and clear internal state."""
        with self._lock:
            for tracker in list(self._trackers.values()):
                tracker.stop()
            self._trackers.clear()

    # ──────────────────────────────────────────────────────────────────────────
    #  Internal tracker
    # ──────────────────────────────────────────────────────────────────────────
    class _PathTracker:
        def __init__(self, handler: FileEventHandler, path: Path):
            self._h = handler
            self.path = path
            self._poll = self._h.settings.__dict__.get(
                "POLL_SECONDS", self._h.POLL_SECONDS
            )
            self._timeout = self._h.settings.__dict__.get(
                "MAX_WAIT_SECONDS", self._h.MAX_WAIT_SECONDS
            )
            self._start = dt.datetime.now()
            self._last_metrics = self._snapshot()
            self._timer: Optional[threading.Timer] = None
            self._schedule()

            logger.debug("Tracker started for %s", path.name)

        # ------------------------- metric helpers -----------------------------
        def _snapshot(self):
            """
            Build a simple, hashable ‘signature’ for the current state.
            Files  : (size, mtime)
            Folders: (file_count, total_size, newest_mtime)
            """
            if not self.path.exists():
                return None

            if self.path.is_file():
                stat = self.path.stat()
                return stat.st_size, stat.st_mtime

            file_count = 0
            total_size = 0
            newest_mtime = 0.0
            for p in self.path.rglob("*"):
                if p.is_file():
                    s = p.stat()
                    file_count += 1
                    total_size += s.st_size
                    newest_mtime = max(newest_mtime, s.st_mtime)
            return file_count, total_size, newest_mtime

        # ---------------------------- loop ------------------------------------
        def _schedule(self):
            self._timer = threading.Timer(self._poll, self._probe)
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

            if (dt.datetime.now() - self._start).total_seconds() >= self._timeout:
                self._reject(f"Timeout (> {self._timeout}s)")
                return

            current = self._snapshot()
            if current != self._last_metrics:
                self._last_metrics = current
                self._schedule()
                return

            # ---------------- stable! ----------------
            if self.path.is_file():
                self._handle_stable_file()
            else:
                self._handle_stable_folder()

        # ---------------- outcome helpers ------------------------------------
        def _handle_stable_file(self):
            if self._h._is_allowed_file(self.path):
                logger.info("File stable & accepted: %s", self.path.name)
                self._h.event_queue.put(str(self.path))
            else:
                self._reject(f"Unsupported file extension '{self.path.suffix}'")

            self.stop()

        def _handle_stable_folder(self):
            exts = {p.suffix.lower() for p in self.path.iterdir() if p.is_file()}
            required = {e.lower() for e in self._h.settings.ALLOWED_FOLDER_CONTENTS}

            if required.issubset(exts):
                logger.info("Folder stable & accepted: %s", self.path.name)
                self._h.event_queue.put(str(self.path))
            else:
                self._reject("Missing required content")

            self.stop()

        def _reject(self, reason: str):
            logger.warning("Folder/File rejected: %s — %s", self.path.name, reason)
            move_to_exception_folder(self.path)
            self._h._rejected.put((str(self.path), reason))

        # ---------------- public ---------------------------------------------
        def stop(self):
            if self._timer:
                self._timer.cancel()
            with self._h._lock:
                self._h._trackers.pop(str(self.path), None)
