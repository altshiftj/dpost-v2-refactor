"""Shared constants defining filesystem defaults and naming conventions."""

import re
import os
from typing import Pattern, List
from pathlib import Path

# --- Directory Paths ---
APP_DIR: Path = Path("C:\\Watchdog")
DESKTOP_DIR: Path = Path(os.path.join(os.environ["USERPROFILE"], "Desktop"))

WATCH_DIR: Path =  DESKTOP_DIR / "Upload"
DEST_DIR: Path =  DESKTOP_DIR / "Data"
RENAME_DIR: Path =  DEST_DIR / "00_To_Rename"
EXCEPTIONS_DIR: Path =  DEST_DIR / "01_Exceptions"
DAILY_RECORDS_JSON: Path =  APP_DIR / "record_persistence.json"

DIRECTORY_LIST: List[Path] = [
    APP_DIR,
    WATCH_DIR,
    DEST_DIR,
    RENAME_DIR,
    EXCEPTIONS_DIR,
]

# --- Naming Conventions ---
ID_SEP: str = "-"
FILE_SEP: str = "_"

# --- Filename Pattern ---
FILENAME_PATTERN: Pattern[str] = re.compile(
r"^(?!.*\.\.)(?!\.)([A-Za-z]+)-[A-Za-z]+-[A-Za-z0-9_ ]{1,30}(?<!\.)$"
)
