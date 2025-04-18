from pathlib import Path
import re
from typing import Set, List, Pattern

class BaseSettings:
    # --- Directory Paths ---
    WATCH_DIR: Path = Path("Upload_Ordner").resolve()
    DEST_DIR: Path = Path("Data").resolve()
    RENAME_DIR: Path = DEST_DIR / "00_To_Rename"
    EXCEPTIONS_DIR: Path = DEST_DIR / "01_Exceptions"
    DAILY_RECORDS_JSON: Path = DEST_DIR / "record_persistence.json"
    LOG_FILE: Path = DEST_DIR / "watchdog.log"

    DIRECTORY_LIST: List[Path] = [
        WATCH_DIR,
        DEST_DIR,
        RENAME_DIR,
        EXCEPTIONS_DIR,
    ]

    # --- Session & Sync ---
    SESSION_TIMEOUT: int = 600
    SYNC_LOGS: bool = True
    LOG_SYNC_INTERVAL: int = 60

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
