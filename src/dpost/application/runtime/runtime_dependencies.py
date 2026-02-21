"""Legacy-backed runtime dependency bindings used by dpost runtime app module."""

from dpost.application.processing import (
    FileProcessManager,
    ProcessingResult,
    ProcessingStatus,
)
from dpost.application.config import ConfigService
from dpost.application.metrics import (
    EVENTS_PROCESSED,
    EXCEPTIONS_THROWN,
    FILE_PROCESS_TIME,
    FILES_FAILED,
    FILES_PROCESSED,
    SESSION_DURATION,
    SESSION_EXIT_STATUS,
)
from dpost.application.session import SessionManager

__all__ = [
    "ConfigService",
    "EVENTS_PROCESSED",
    "EXCEPTIONS_THROWN",
    "FILE_PROCESS_TIME",
    "FILES_FAILED",
    "FILES_PROCESSED",
    "FileProcessManager",
    "ProcessingResult",
    "ProcessingStatus",
    "SESSION_DURATION",
    "SESSION_EXIT_STATUS",
    "SessionManager",
]
