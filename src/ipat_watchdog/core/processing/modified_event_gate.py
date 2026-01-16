"""Scoped modified-event gating for file processing."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from ipat_watchdog.core.config import ConfigService, DeviceConfig
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS

logger = setup_logger(__name__)


class ModifiedEventGate:
    """Decides whether a modified filesystem event should be queued."""

    def __init__(
        self,
        config_service: ConfigService,
        processor_resolver: Callable[[DeviceConfig], FileProcessorABS],
        cooldown_seconds: float = 1.0,
        prune_after_seconds: float | None = None,
        prune_interval_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._config_service = config_service
        self._processor_resolver = processor_resolver
        self._cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._last_seen: dict[str, float] = {}
        self._prune_after_seconds = self._resolve_prune_after(prune_after_seconds)
        self._prune_interval_seconds = self._resolve_prune_interval(prune_interval_seconds)
        self._next_prune_at = self._clock() + self._prune_interval_seconds

    def should_queue(self, path: str) -> bool:
        target = Path(path)
        if target.is_dir():
            return False

        candidates = self._config_service.matching_devices(target)
        if not candidates:
            return False

        for device in candidates:
            processor = self._processor_resolver(device)
            try:
                if processor.should_queue_modified(str(target)):
                    return self._allow_modified_event(target)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Modified event check failed for %s: %s", target, exc)

        return False

    def _allow_modified_event(self, path: Path) -> bool:
        key = str(path.resolve())
        now = self._clock()
        self._maybe_prune(now)
        last_seen = self._last_seen.get(key)
        if last_seen is not None and (now - last_seen) < self._cooldown_seconds:
            return False
        self._last_seen[key] = now
        return True

    def _resolve_prune_after(self, prune_after_seconds: float | None) -> float:
        if prune_after_seconds is None:
            prune_after_seconds = max(self._cooldown_seconds * 2, 60.0)
        return max(prune_after_seconds, self._cooldown_seconds)

    def _resolve_prune_interval(self, prune_interval_seconds: float | None) -> float:
        if prune_interval_seconds is None:
            prune_interval_seconds = self._prune_after_seconds
        return max(prune_interval_seconds, self._cooldown_seconds)

    def _maybe_prune(self, now: float) -> None:
        if now < self._next_prune_at:
            return
        self._next_prune_at = now + self._prune_interval_seconds
        cutoff = now - self._prune_after_seconds
        if cutoff <= 0:
            return
        stale = [key for key, seen_at in self._last_seen.items() if seen_at < cutoff]
        for key in stale:
            del self._last_seen[key]
