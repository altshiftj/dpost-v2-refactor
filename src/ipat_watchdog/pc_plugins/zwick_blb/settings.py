from pathlib import Path
import re
from typing import List, Pattern, Optional, Tuple
import os
from ipat_watchdog.core.config.pc_settings import PCSettings

class PCZwickSettings(PCSettings):
    """Lab workstation specific settings with optimized configuration for active lab work."""
    
    SESSION_TIMEOUT: int = 600  # seconds

    POLL_SECONDS: float = 1.5
    MAX_WAIT_SECONDS: float = 30.0
    STABLE_CYCLES: int = 3
    TEMP_FOLDER_REGEX: Pattern[str] = re.compile(r"\.[A-Za-z0-9]{6}$")

