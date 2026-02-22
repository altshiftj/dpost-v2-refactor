"""Logging helpers that emit structured JSON to disk and stdout."""

from __future__ import annotations

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE_DIR = Path("C:/Watchdog")
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "watchdog.log"
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


class JSONFormatter(logging.Formatter):
    """Formatter that serializes log records into JSON payloads."""

    def format(self, record: logging.LogRecord) -> str:
        """Format one log record as a JSON line."""
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "filename": record.filename,
            "line": record.lineno,
        }
        session_id = getattr(record, "session_id", None)
        if session_id is not None:
            payload["session_id"] = session_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def _parse_bool_env(value: str | None) -> bool | None:
    """Parse a boolean-ish environment variable value."""
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return None


def _is_pytest_runtime() -> bool:
    """Detect pytest execution so file logging can default off in tests."""
    return "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ


def _file_logging_enabled() -> bool:
    """Resolve whether rotating file logging should be attached."""
    configured = _parse_bool_env(os.getenv("DPOST_LOG_FILE_ENABLED"))
    if configured is not None:
        return configured
    return not _is_pytest_runtime()


def _resolve_log_file_path() -> Path:
    """Resolve the log file path from environment overrides or defaults."""
    override = os.getenv("DPOST_LOG_FILE_PATH") or os.getenv("LOG_FILE_PATH")
    if override:
        return Path(override)
    return LOG_FILE


def setup_logger(name: str = "watchdog") -> logging.Logger:
    """Return a configured logger with JSON handlers and optional file output."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    # Preserve pytest caplog capture (root-handler based) while preventing
    # duplicate host-process logging in normal runtime execution.
    logger.propagate = _is_pytest_runtime()

    if not logger.handlers:
        formatter = JSONFormatter()
        if _file_logging_enabled():
            try:
                log_path = _resolve_log_file_path()
                log_path.parent.mkdir(parents=True, exist_ok=True)
                file_handler = RotatingFileHandler(
                    str(log_path), maxBytes=5_000_000, backupCount=3
                )
                file_handler.setFormatter(formatter)
                file_handler.setLevel(logging.DEBUG)
                logger.addHandler(file_handler)
            except Exception:  # noqa: BLE001
                # Logging setup must not fail application/test startup due to file access.
                pass

        if sys.stdout:
            try:
                console_handler = logging.StreamHandler(stream=sys.stdout)
                console_handler.setFormatter(formatter)
                console_handler.setLevel(logging.DEBUG)
                logger.addHandler(console_handler)
            except Exception:  # noqa: BLE001
                pass

        if not logger.handlers:
            logger.addHandler(logging.NullHandler())

    return logger
