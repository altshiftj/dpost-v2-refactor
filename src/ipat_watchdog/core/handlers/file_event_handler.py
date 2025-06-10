from __future__ import annotations

"""
FileEventHandler – v3  (adaptive debounce + fast invalid-content reject)
=======================================================================
 ▸ Fast accept   : valid folder ≈ 4 s   (2 s idle  + 2 s confirm)
 ▸ Fast reject   : invalid folder ≈ 4 s (2 s idle  + 2 s confirm)
 ▸ Slow debounce : accept after 30 s idle
 ▸ Hard timeout  : reject after 90 s idle

Defaults (override in Settings):
    FAST_PROBE_IDLE_SECONDS ...... 2
    FAST_CONFIRM_WINDOW_SECONDS .. 2
    SLOW_DEBOUNCE_SECONDS ........ 30
    FOLDER_STABILITY_TIMEOUT ..... 90
"""

import datetime as dt
import enum
import threading
from pathlib import Path
from queue import Queue
from typing import Dict, Optional, Set, Tuple

from watchdog.events import FileSystemEvent, FileSystemEventHandler

from ipat_watchdog.core.config.settings_base import BaseSettings
from ipat_watchdog.core.config.settings_store import SettingsStore
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.storage.filesystem_utils import move_to_exception_folder

logger = setup_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
#  Top-level handler
# ──────────────────────────────────────────────────────────────────────────────
class FileEventHandler(FileSystemEventHandler):
    """Debounces single files and tracks multi-file folders until they’re stable."""

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

    # ------------------------------------------------------------------ shutdown
    def shutdown(self) -> None:
        with self._lock:
            for t in self._timers.values():
                t.cancel()
            for tr in list(self._folder_trackers.values()):
                tr._cleanup()
            self._timers.clear()
            self._folder_trackers.clear()
        logger.debug("FileEventHandler shutdown: timers & trackers cancelled")

    # -------------------------------------------------------------- file system
    def on_created(self, event: FileSystemEvent) -> None:  # noqa: N802 (watchdog)
        path = Path(event.src_path)

        if self._reject_now_if_invalid_single_file(path):
            return

        if path.is_dir():
            self._start_folder_tracker(path)
        else:
            self._schedule_file_debounce(path)

    # ───────────────────────────── single-file debounce ────────────────────────
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
                getattr(self.settings, "FAST_DEBOUNCE_SECONDS", 1)
                if self._is_expedited_file(path)
                else getattr(self.settings, "SLOW_DEBOUNCE_SECONDS", 30)
            )

            def _callback() -> None:
                try:
                    self._finalise_single_file(path_str)
                except Exception:
                    logger.exception("Unhandled error finalising file: %s", path_str)

            timer = threading.Timer(delay, _callback)
            self._timers[path_str] = timer
            logger.debug("Started %s-s debounce for file: %s", delay, path.name)
            timer.start()

    def _finalise_single_file(self, path_str: str) -> None:
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
            move_to_exception_folder(path)

    # ─────────────────────────── “building” folder tracker ──────────────────────
    class _ProbeState(enum.Enum):
        NONE = enum.auto()
        FAST_VALID = enum.auto()
        FAST_INVALID = enum.auto()

    class _FolderTracker:
        """Tracks a single folder until accepted or rejected."""

        def __init__(self, handler: "FileEventHandler", folder: Path, poll: float = 1.0):
            self._h = handler
            self.folder = folder
            self._poll_interval = poll

            self.last_change = dt.datetime.now()
            self.last_exts: Set[str] = set()

            self._probe_state = FileEventHandler._ProbeState.NONE
            self._probe_started: Optional[dt.datetime] = None

            self._timer: Optional[threading.Timer] = None
            self._schedule_next()
            logger.debug("Folder tracker started: %s", folder.name)

        # ------------------------ helpers to read settings ----------------------
        def _s(self, name: str, default: int) -> int:
            return getattr(self._h.settings, name, default)

        @property
        def _idle_fast(self) -> int:
            return self._s("FAST_PROBE_IDLE_SECONDS", 2)

        @property
        def _confirm_fast(self) -> int:
            return self._s("FAST_CONFIRM_WINDOW_SECONDS", 2)

        @property
        def _debounce_slow(self) -> int:
            return self._s("SLOW_DEBOUNCE_SECONDS", 30)

        @property
        def _timeout(self) -> int:
            return self._s("FOLDER_STABILITY_TIMEOUT", 90)

        # ------------------------------- polling loop --------------------------
        @property
        def idle(self) -> float:
            return (dt.datetime.now() - self.last_change).total_seconds()

        def _schedule_next(self) -> None:
            self._timer = threading.Timer(self._poll_interval, self._safe_poll)
            self._timer.start()

        def _safe_poll(self) -> None:
            try:
                self._poll()
            except Exception:
                logger.exception("Polling crashed for %s", self.folder)
                self._cleanup()

        def _poll(self) -> None:
            # vanished?
            if not self.folder.exists():
                self._cleanup()
                return

            try:
                exts = {p.suffix.lower() for p in self.folder.iterdir() if p.is_file()}
            except Exception as exc:
                self._finish_reject(f"I/O error: {exc}")
                return

            # content change ⇒ reset timers / probes
            if exts != self.last_exts:
                self.last_exts = exts
                self.last_change = dt.datetime.now()
                self._probe_state = FileEventHandler._ProbeState.NONE
                self._probe_started = None

            required = {e.lower() for e in self._h.settings.ALLOWED_FOLDER_CONTENTS}
            idle = self.idle
            now = dt.datetime.now()

            # 1) fast-probe: accept or reject in ≈4 s
            if idle >= self._idle_fast:
                if required.issubset(exts):          # candidate for fast-accept
                    self._do_fast(now, accept=True, idle=idle)
                else:                                # candidate for fast-reject
                    self._do_fast(now, accept=False, idle=idle)

            # 2) slow-debounce accept (30 s)
            if required.issubset(exts) and idle >= self._debounce_slow:
                self._accept(f"slow-debounce (idle {idle:.1f}s)")
                return

            # 3) hard timeout reject (90 s)
            if idle >= self._timeout:
                self._finish_reject(f"timeout (idle {idle:.1f}s)")
                return

            self._schedule_next()

        # ------------------------------ fast-probe -----------------------------
        def _do_fast(self, now: dt.datetime, *, accept: bool, idle: float) -> None:
            desired = (
                FileEventHandler._ProbeState.FAST_VALID
                if accept
                else FileEventHandler._ProbeState.FAST_INVALID
            )

            if self._probe_state is FileEventHandler._ProbeState.NONE:
                self._probe_state = desired
                self._probe_started = now
                logger.debug(
                    "%s fast-probe opened (idle %.1fs): %s",
                    "ACCEPT" if accept else "REJECT",
                    idle,
                    self.folder.name,
                )
                return

            if self._probe_state is desired:
                age = (now - (self._probe_started or now)).total_seconds()
                if age >= self._confirm_fast:
                    if accept:
                        self._accept(f"fast accept (idle {idle:.1f}s)")
                    else:
                        self._finish_reject(f"fast reject (idle {idle:.1f}s)")

        # ------------------------- outcome helpers ----------------------------
        def _accept(self, note: str) -> None:
            logger.info("Folder accepted: %s — %s", self.folder.name, note)
            self._h.event_queue.put(str(self.folder))
            self._cleanup()

        def _finish_reject(self, reason: str) -> None:
            logger.warning("Folder rejected %s — %s", self.folder.name, reason)
            move_to_exception_folder(str(self.folder), filename_prefix=self.folder.name, extension="")
            self._h._rejected.put((str(self.folder), reason))
            self._cleanup()

        def _cleanup(self) -> None:
            if self._timer:
                self._timer.cancel()
            with self._h._lock:
                self._h._folder_trackers.pop(str(self.folder), None)

    # ───────────────────── tracker factory & validation helpers ──────────────────
    def _start_folder_tracker(self, folder: Path) -> None:
        with self._lock:
            if len(self._folder_trackers) >= self._max_active_trackers:
                reason = "Folder tracker limit reached – skipping"
                logger.warning("%s: %s", reason, folder.name)
                self._rejected.put((str(folder), reason))
                return

            pstr = str(folder)
            if pstr in self._folder_trackers:
                self._folder_trackers[pstr]._cleanup()

            self._folder_trackers[pstr] = self._FolderTracker(self, folder)
        logger.debug("Started folder tracker for: %s", folder.name)

    # ---------------------------------------------------------------- validation
    def _reject_now_if_invalid_single_file(self, path: Path) -> bool:
        if path.is_file() and not self._should_accept_file(path):
            reason = f"Unsupported file extension '{path.suffix}'"
            logger.warning("Rejected immediately: %s — %s", path.name, reason)
            move_to_exception_folder(path)
            self._rejected.put((str(path), reason))
            return True
        return False

    def _should_accept_file(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in self.settings.ALLOWED_EXTENSIONS

    def _is_expedited_file(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in self.settings.EXPEDITED_EXTENSIONS

    # ---------------------------------------------------------------- rejected‐log
    def get_and_clear_rejected(self) -> list[Tuple[str, str]]:
        items: list[Tuple[str, str]] = []
        while not self._rejected.empty():
            items.append(self._rejected.get())
        return items
