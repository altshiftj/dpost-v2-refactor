"""Synchronous stability guard that blocks until a file stops changing."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import datetime as dt
import time
from typing import Any, Iterable, Optional

from ipat_watchdog.core.logging.logger import setup_logger

logger = setup_logger(__name__)


@dataclass(frozen=True)
class StabilityOutcome:
    """Result of waiting for a file/folder to settle."""

    path: Path
    stable: bool
    reason: Optional[str] = None

    @property
    def rejected(self) -> bool:
        return not self.stable


class FileStabilityTracker:
    """Inline (blocking) stability tracker used by the processing pipeline."""

    def __init__(self, file_path: Path, device_settings: Any) -> None:
        self.file_path = Path(file_path)
        self.device_settings = device_settings

    def wait(self) -> StabilityOutcome:
        deadline = dt.datetime.now() + dt.timedelta(seconds=self._max_wait_seconds())
        last_snapshot = self._snapshot()
        stable_cycles = 0

        poll_seconds = self._poll_seconds()

        while True:
            if not self.file_path.exists():
                return StabilityOutcome(
                    path=self.file_path,
                    stable=False,
                    reason="Path disappeared before becoming stable",
                )

            if dt.datetime.now() >= deadline:
                return StabilityOutcome(
                    path=self.file_path,
                    stable=False,
                    reason=f"Timeout (> {self._max_wait_seconds()}s)",
                )

            current_snapshot = self._snapshot()
            if current_snapshot != last_snapshot:
                last_snapshot = current_snapshot
                stable_cycles = 0
                self._sleep(poll_seconds)
                continue

            stable_cycles += 1
            if stable_cycles < self._stable_cycles():
                self._sleep(poll_seconds)
                continue

            if self._await_sentinel(poll_seconds):
                continue

            logger.info(
                "File/folder is stable: %s", self.file_path.name
            )
            return StabilityOutcome(path=self.file_path, stable=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _await_sentinel(self, poll_seconds: float) -> bool:
        """Return True if we must wait for a sentinel to appear."""
        sentinel_name = getattr(self.device_settings, "SENTINEL_NAME", None)
        if not sentinel_name or not self.file_path.is_dir():
            return False
        sentinel_path = self.file_path / sentinel_name
        if sentinel_path.exists():
            return False
        logger.debug("Waiting for sentinel '%s' in %s", sentinel_name, self.file_path)
        self._sleep(poll_seconds)
        return True

    def _snapshot(self):
        if not self.file_path.exists():
            return None
        if self.file_path.is_file():
            stat = self.file_path.stat()
            return stat.st_size, stat.st_mtime
        file_count = 0
        total_size = 0
        newest_mtime = 0.0
        for child in self._iter_files(self.file_path):
            try:
                stat = child.stat()
            except FileNotFoundError:
                continue
            file_count += 1
            total_size += stat.st_size
            newest_mtime = max(newest_mtime, stat.st_mtime)
        return file_count, total_size, newest_mtime

    def _iter_files(self, directory: Path) -> Iterable[Path]:
        temp_patterns = getattr(self.device_settings, "TEMP_PATTERNS", tuple())
        if isinstance(temp_patterns, str):
            temp_patterns = (temp_patterns,)
        temp_patterns = tuple(p.lower() for p in temp_patterns)

        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            if temp_patterns and path.name.lower().endswith(temp_patterns):
                continue
            yield path

    def _poll_seconds(self) -> float:
        try:
            return max(float(getattr(self.device_settings, "POLL_SECONDS", 1.0)), 0.0)
        except Exception:
            return 1.0

    def _max_wait_seconds(self) -> int:
        try:
            return int(getattr(self.device_settings, "MAX_WAIT_SECONDS", 300))
        except Exception:
            return 300

    def _stable_cycles(self) -> int:
        try:
            return int(getattr(self.device_settings, "STABLE_CYCLES", 3))
        except Exception:
            return 3

    @staticmethod
    def _sleep(seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)
