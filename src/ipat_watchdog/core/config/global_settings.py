from pathlib import Path
import re
from typing import Set, List, Pattern, Optional, Tuple
import os

class PCSettings:
    """Application-wide configuration."""
    
    def __init__(self):
        """Initialize global settings with default or environment-specific values."""
        # --- Directory Paths ---
        self.APP_DIR: Path = Path("C:\\Watchdog")
        self.DESKTOP_DIR: Path = Path(os.path.join(os.environ["USERPROFILE"], "Desktop"))

        self.WATCH_DIR: Path = self.DESKTOP_DIR / "Upload"
        self.DEST_DIR: Path = self.DESKTOP_DIR / "Data"
        self.RENAME_DIR: Path = self.DEST_DIR / "00_To_Rename"
        self.EXCEPTIONS_DIR: Path = self.DEST_DIR / "01_Exceptions"
        self.DAILY_RECORDS_JSON: Path = self.APP_DIR / "record_persistence.json"

        self.DIRECTORY_LIST: List[Path] = [
            self.APP_DIR,
            self.WATCH_DIR,
            self.DEST_DIR,
            self.RENAME_DIR,
            self.EXCEPTIONS_DIR,
        ]

        # --- Session ---
        self.SESSION_TIMEOUT: int = -1

        # --- Naming Conventions ---
        self.ID_SEP: str = "-"
        self.FILE_SEP: str = "_"

        # --- Filename Pattern ---
        self.FILENAME_PATTERN: Pattern[str] = re.compile(
            r"^(?!.*\.\.)(?!\.)([A-Za-z]+)-[A-Za-z]+-[A-Za-z0-9_ ]{1,30}+(?<!\.)$"
        )

        # === Snapshot Watcher Settings ===
        self.POLL_SECONDS: float = -1
        self.MAX_WAIT_SECONDS: float = -1
        self.STABLE_CYCLES: int = -1
        self.TEMP_PATTERNS: Tuple[str, ...] = ('.tmp', '.part', '.crdownload', '.~', '-journal')
        self.TEMP_FOLDER_REGEX: Pattern[str] = re.compile(r"\.[A-Za-z0-9]{6}$")
        self.SENTINEL_NAME: Optional[str] = None
