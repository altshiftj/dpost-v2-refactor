"""
Device-aware file/folder stability tracking utilities.

Synchronous (inline) FileStabilityTracker that waits until files or
directories are fully written before proceeding. Designed to run in a
single-threaded environment where only one file is processed at a time,
so it does not rely on UI scheduling callbacks.

Kept intentionally independent from FileProcessManager so it can be reused
by watchers or other orchestrators in the future.
"""
from __future__ import annotations

from pathlib import Path
import datetime as dt
import time
from typing import Callable, Any, Optional

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.storage.filesystem_utils import move_to_exception_folder

logger = setup_logger(__name__)


class FileStabilityTracker:
    """
    Device-aware file stability tracker (synchronous/inline).

    Uses device-specific settings for polling intervals, stability criteria,
    temp file patterns, and sentinel file requirements.

    Callbacks:
    - completion_callback(path: str): invoked when the path is stable
    - rejection_callback(path: str, reason: str): invoked if rejected
    """

    def __init__(
        self,
        file_path: Path,
        device_settings: Any,
        completion_callback: Callable[[str], None],
        rejection_callback: Callable[[str, str], None],
    ) -> None:
        self.file_path = file_path
        self.device_settings = device_settings
        self.completion_callback = completion_callback
        self.rejection_callback = rejection_callback

        self._start_time = dt.datetime.now()
        self._last_metrics = self._snapshot()
        self._stable_count = 0
        self._stopped = False
        self._completed = False

        logger.debug(
            f"Stability tracker started for {file_path.name} with device {getattr(device_settings, 'DEVICE_ID', 'unknown')}"
        )
        # Run synchronously until completion/rejection/stop
        self._run_inline()

    def _snapshot(self):
        """Take snapshot of file/folder state for stability comparison."""
        if not self.file_path.exists():
            return None

        if self.file_path.is_file():
            s = self.file_path.stat()
            return s.st_size, s.st_mtime

        # For folders - count files and total size, excluding temp files
        file_count = 0
        total_size = 0
        newest_mtime = 0.0

        for p in self.file_path.rglob("*"):
            if p.is_file() and not p.name.endswith(self.device_settings.TEMP_PATTERNS):
                try:
                    s = p.stat()
                    file_count += 1
                    total_size += s.st_size
                    newest_mtime = max(newest_mtime, s.st_mtime)
                except FileNotFoundError:
                    continue

        return file_count, total_size, newest_mtime

    def _evaluate(self) -> tuple[str, Optional[str]]:
        """
        Evaluate the current stability state once.

        Returns a tuple (state, reason) where state is one of:
        - 'continue': not yet stable, keep checking
        - 'complete': stable and ready
        - 'reject': cannot proceed (reason provided)
        """
        if not self.file_path.exists():
            return "reject", "Path disappeared before becoming stable"

        # Check for timeout
        elapsed = (dt.datetime.now() - self._start_time).total_seconds()
        if elapsed >= self.device_settings.MAX_WAIT_SECONDS:
            return "reject", f"Timeout (> {self.device_settings.MAX_WAIT_SECONDS}s)"

        # Compare current state with last snapshot
        current = self._snapshot()
        if current != self._last_metrics:
            # Still changing - reset stability counter
            self._last_metrics = current
            self._stable_count = 0
            return "continue", None

        # Increment stability counter
        self._stable_count += 1
        if self._stable_count < self.device_settings.STABLE_CYCLES:
            # Not stable enough yet
            return "continue", None

        # Check sentinel file requirement for folders
        if self.file_path.is_dir() and getattr(self.device_settings, "SENTINEL_NAME", None):
            sentinel = self.file_path / self.device_settings.SENTINEL_NAME
            if not sentinel.exists():
                logger.debug(
                    f"Waiting for sentinel {sentinel.name} in {self.file_path.name}"
                )
                return "continue", None

        # File/folder is stable
        return "complete", None

    def _run_inline(self) -> None:
        """Run synchronous stability probing loop (no UI scheduling)."""
        try:
            poll_seconds = max(float(getattr(self.device_settings, "POLL_SECONDS", 1.0)), 0.0)
        except Exception:
            poll_seconds = 1.0

        try:
            while not self._stopped and not self._completed:
                try:
                    state, reason = self._evaluate()
                except Exception as e:
                    logger.exception(f"Stability tracker error for {self.file_path}: {e}")
                    self._reject(f"Tracking error: {e}")
                    break

                if state == "reject":
                    self._reject(reason or "Rejected")
                    break

                if state == "complete":
                    logger.info(
                        f"{'Folder' if self.file_path.is_dir() else 'File'} stable & ready: {self.file_path.name}"
                    )
                    self._completed = True
                    self.completion_callback(str(self.file_path))
                    break

                # continue
                if poll_seconds > 0:
                    time.sleep(poll_seconds)
        finally:
            # Nothing to cancel in inline mode
            pass

    def _reject(self, reason: str) -> None:
        """Handle rejection of unstable or problematic files."""
        if not self.file_path.exists():
            logger.debug(f"Path vanished during rejection: {self.file_path.name}")
            self.stop()
            return

        logger.warning(f"File/Folder rejected: {self.file_path.name} — {reason}")
        move_to_exception_folder(self.file_path)
        self.rejection_callback(str(self.file_path), reason)
        self.stop()

    def stop(self) -> None:
        """Stop the stability tracker."""
        self._stopped = True
        # No scheduler handle to cancel in synchronous mode
