from pathlib import Path
import re
from typing import Set, List, Pattern
import os

class BaseSettings:
    # --- Directory Paths ---
    APP_DIR: Path = Path("C:\\Program Files\\Watchdog")
    DESKTOP_DIR: Path = Path(os.path.join(os.environ["USERPROFILE"], "Desktop"))

    # --- Directory Paths ---
    WATCH_DIR: Path = DESKTOP_DIR / "Upload_Ordner"
    DEST_DIR: Path = DESKTOP_DIR / "Data"
    RENAME_DIR: Path = DEST_DIR / "00_To_Rename"
    EXCEPTIONS_DIR: Path = DEST_DIR / "01_Exceptions"
    DAILY_RECORDS_JSON: Path = APP_DIR / "record_persistence.json"

    DIRECTORY_LIST: List[Path] = [
        APP_DIR,
        DESKTOP_DIR,
        WATCH_DIR,
        DEST_DIR,
        RENAME_DIR,
        EXCEPTIONS_DIR,
    ]

    # --- Session ---
    SESSION_TIMEOUT: int = 600

    # --- Naming Conventions ---
    ID_SEP: str = "-"
    FILE_SEP: str = "_"
    DEBOUNCE_TIME: int = 2 # seconds
    ALLOWED_EXTENSIONS: Set[str] = {".txt", ".csv", ".json"}
    FILENAME_PATTERN: Pattern[str] = re.compile(
        r"^(?!.*\.\.)(?!\.)([A-Za-z]+)-[A-Za-z]+-[A-Za-z0-9_ ]{1,30}+(?<!\.)$"
    )

    DEVICE_USER_KADI_ID: str = "undefined-device-user"
    DEVICE_USER_PERSISTENT_ID: int = -1
    DEVICE_RECORD_PERSISTENT_ID: int = -1
    DEVICE_TYPE: str = "GENERIC"
    RECORD_TAGS: List[str] = ["Generic Tag"]

    DEFAULT_RECORD_DESCRIPTION: str = (
        "No description set. Override `DEFAULT_RECORD_DESCRIPTION` in device settings."
    )
