from abc import ABC
from typing import Set, Pattern
import re

class DeviceSettings(ABC):
    """Base class for device-specific configuration."""
    # Device identity - make DEVICE_ID optional for backward compatibility
    DEVICE_ID: str = ''
    DEVICE_TYPE: str = ''
    DEVICE_USER_KADI_ID: str = ''
    ALLOWED_EXTENSIONS: Set[str] = set()
    FILENAME_PATTERN: Pattern[str] = re.compile(r'.*')
    SESSION_TIMEOUT: int = 300
    POLL_SECONDS: float = 1.0

    def get_device_id(self) -> str:
        """Get device ID, falling back to DEVICE_TYPE if DEVICE_ID not set."""
        return self.DEVICE_ID or getattr(self, 'DEVICE_TYPE', 'unknown')

    def matches_file(self, filepath: str) -> bool:
        """Check if this device can process the given file."""
        # Check extension
        if not any(filepath.lower().endswith(ext) for ext in self.ALLOWED_EXTENSIONS):
            return False
        
        # Check filename pattern (without extension)
        from pathlib import Path
        filename_without_ext = Path(filepath).stem
        return bool(self.FILENAME_PATTERN.match(filename_without_ext))
