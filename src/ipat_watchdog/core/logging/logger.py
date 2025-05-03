# logger.py
import logging
import json
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

BASE_DIR = Path("C:/Watchdog")
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "watchdog.log"

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "filename": record.filename,
            "line": record.lineno,
        }
        if hasattr(record, "session_id"):
            log_record["session_id"] = record.session_id
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logger(name: str = "watchdog") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        formatter = JSONFormatter()

        # File handler
        file_handler = RotatingFileHandler(str(LOG_FILE), maxBytes=5_000_000, backupCount=3)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

        if sys.stdout:
            try:
                console_handler = logging.StreamHandler(stream=sys.stdout)
                console_handler.setFormatter(formatter)
                console_handler.setLevel(logging.DEBUG)
                logger.addHandler(console_handler)
            except Exception:
                pass

    return logger
