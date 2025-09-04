from pathlib import Path
import re
from typing import List, Pattern, Optional, Tuple
import os
from ipat_watchdog.core.config.global_settings import PCSettings

class LabWorkstationSettings(PCSettings):
    """Lab workstation specific settings with optimized configuration for active lab work."""
    
    # Override default paths for lab environment
    WATCH_DIR: Path = Path("D:\\LabData\\Upload")
    DEST_DIR: Path = Path("D:\\LabData\\Processed")
    RENAME_DIR: Path = DEST_DIR / "00_To_Rename"
    EXCEPTIONS_DIR: Path = DEST_DIR / "01_Exceptions"
    
    # Lab-specific directory list (override parent)
    DIRECTORY_LIST: List[Path] = [
        PCSettings.APP_DIR,  # Keep the standard app dir
        WATCH_DIR,
        DEST_DIR,
        RENAME_DIR,
        EXCEPTIONS_DIR,
    ]
    
    # Faster polling for active lab work
    POLL_SECONDS: float = 0.5
    MAX_WAIT_SECONDS: float = 2.0
    STABLE_CYCLES: int = 2
    
    # Lab-specific filename pattern (requires LAB prefix)
    FILENAME_PATTERN: Pattern[str] = re.compile(
        r"^LAB-[A-Za-z]+-[A-Za-z0-9_ ]{1,30}+(?<!\.)$"
    )
