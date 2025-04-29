# logger.py
import logging
import json
import sys
from datetime import datetime

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
        if record.__dict__.get("session_id"):
            log_record["session_id"] = record.session_id
        return json.dumps(log_record)

def setup_logger(name: str = "watchdog") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(JSONFormatter())
        console_handler.setLevel(logging.DEBUG)
        logger.addHandler(console_handler)

    return logger
