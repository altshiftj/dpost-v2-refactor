# ──────────────────────────────────────────────────────────────────────────────
#  src/ipat_watchdog/app/logger.py
# ──────────────────────────────────────────────────────────────────────────────
import logging
import json
from datetime import datetime
from pathlib import Path

# ─── Global paths ─────────────────────────────────────────────────────────────
LOG_DIR = Path("Data")
LOG_DIR.mkdir(exist_ok=True)

LOG_TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_PATH_HUMAN = LOG_DIR / "watchdog.log"
LOG_PATH_JSON  = LOG_DIR / f"watchdog_structured_{LOG_TIMESTAMP}.json"

# ─── JSON formatter ───────────────────────────────────────────────────────────
class JSONFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "filename": record.filename,
            "line": record.lineno,
        }
        if record.__dict__.get("session_id"):
            entry["session_id"] = record.session_id
        return json.dumps(entry)

# ─── Logger factory ───────────────────────────────────────────────────────────
def setup_logger(name: str = "watchdog") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Human log
        human_fmt = logging.Formatter(
            "%(asctime)s - %(pathname)s - %(levelname)s - %(message)s"
        )
        human_handler = logging.FileHandler(LOG_PATH_HUMAN)
        human_handler.setFormatter(human_fmt)
        human_handler.setLevel(logging.DEBUG)
        logger.addHandler(human_handler)

        LOG_PATH_HUMAN.touch(exist_ok=True)

        # JSON log
        json_handler = logging.FileHandler(LOG_PATH_JSON)
        json_handler.setFormatter(JSONFormatter())
        json_handler.setLevel(logging.DEBUG)
        logger.addHandler(json_handler)

        # Console
        console = logging.StreamHandler()
        console.setFormatter(human_fmt)
        console.setLevel(logging.INFO)
        logger.addHandler(console)

    return logger
