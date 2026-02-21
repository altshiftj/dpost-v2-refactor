"""Prometheus metric definitions tracked by the dpost runtime application."""

from __future__ import annotations

from typing import Iterable

from prometheus_client import REGISTRY, Counter, Gauge, Histogram


def _existing_collector(name: str):
    names_to_collectors = getattr(REGISTRY, "_names_to_collectors", {})
    return names_to_collectors.get(name) or names_to_collectors.get(f"{name}_total")


def _counter(name: str, documentation: str, labelnames: Iterable[str] = ()):
    existing = _existing_collector(name)
    if isinstance(existing, Counter):
        return existing
    return Counter(name, documentation, tuple(labelnames))


def _gauge(name: str, documentation: str):
    existing = _existing_collector(name)
    if isinstance(existing, Gauge):
        return existing
    return Gauge(name, documentation)


def _histogram(name: str, documentation: str):
    existing = _existing_collector(name)
    if isinstance(existing, Histogram):
        return existing
    return Histogram(name, documentation)


FILES_PROCESSED = _counter("files_processed", "Total files processed by Watchdog")

FILES_PROCESSED_BY_RECORD = _counter(
    "files_processed_by_record",
    "Files processed by record ID",
    ["record_id"],
)

FILES_FAILED = _counter("files_failed", "Files that failed to process due to errors")

EVENTS_PROCESSED = _counter(
    "events_processed",
    "Total file system events triggered in this session",
)

FILE_PROCESS_TIME = _histogram(
    "file_process_time_seconds",
    "Time spent processing individual files",
)

SESSION_EXIT_STATUS = _gauge("session_exit_status", "0 = clean exit, 1 = crashed")

SESSION_DURATION = _gauge(
    "session_duration_seconds",
    "Total duration of WatchdogApp session in seconds",
)

EXCEPTIONS_THROWN = _counter(
    "exceptions_thrown",
    "Total uncaught exceptions during app runtime",
)

__all__ = [
    "EVENTS_PROCESSED",
    "EXCEPTIONS_THROWN",
    "FILE_PROCESS_TIME",
    "FILES_FAILED",
    "FILES_PROCESSED",
    "FILES_PROCESSED_BY_RECORD",
    "SESSION_DURATION",
    "SESSION_EXIT_STATUS",
]
