"""Logging helpers that emit structured JSON to disk and stdout."""

from __future__ import annotations

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE_DIR = Path("C:/Watchdog")
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "watchdog.log"


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


def setup_logger(name: str = "watchdog") -> logging.Logger:
    """Return a configured logger with rotating file + stdout JSON handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        formatter = JSONFormatter()

        file_handler = RotatingFileHandler(
            str(LOG_FILE), maxBytes=5_000_000, backupCount=3
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

        if sys.stdout:
            try:
                console_handler = logging.StreamHandler(stream=sys.stdout)
                console_handler.setFormatter(formatter)
                console_handler.setLevel(logging.DEBUG)
                logger.addHandler(console_handler)
            except Exception:  # noqa: BLE001
                pass

    return logger
