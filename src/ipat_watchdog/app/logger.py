# logger.py
import logging
import json
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Define base log directory inside Program Files
BASE_DIR = Path("C:/Program Files/Watchdog")
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
        return json.dumps(log_record)

def setup_logger(name: str = "watchdog") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        formatter = JSONFormatter()

        # File handler
        file_handler = RotatingFileHandler(str(LOG_FILE), maxBytes=1_000_000, backupCount=3)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

        # Console handler (dev use only)
        if sys.stdout:
            try:
                console_handler = logging.StreamHandler(stream=sys.stdout)
                console_handler.setFormatter(formatter)
                console_handler.setLevel(logging.DEBUG)
                logger.addHandler(console_handler)
            except Exception:
                pass

    return logger

# Default logger
logger = setup_logger()
