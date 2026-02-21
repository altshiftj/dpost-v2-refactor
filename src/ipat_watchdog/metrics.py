"""Legacy import path compatibility wrappers for dpost-owned metrics."""

from dpost.application.metrics import (
    EVENTS_PROCESSED,
    EXCEPTIONS_THROWN,
    FILE_PROCESS_TIME,
    FILES_FAILED,
    FILES_PROCESSED,
    FILES_PROCESSED_BY_RECORD,
    SESSION_DURATION,
    SESSION_EXIT_STATUS,
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
