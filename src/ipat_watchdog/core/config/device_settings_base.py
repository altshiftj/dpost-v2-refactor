from typing import Set, List
from abc import ABC
from pathlib import Path

class DeviceSettings(ABC):
    """Base class for device-specific configuration."""
    # --- Device Metadata ---
    DEVICE_USER_KADI_ID: str = "undefined-device-user"
    DEVICE_USER_PERSISTENT_ID: int = -1
    DEVICE_RECORD_KADI_ID = "udr_01"
    DEVICE_RECORD_PERSISTENT_ID: int = -1
    DEVICE_TYPE: str = "GENERIC"
    DEVICE_ID: str = "generic"  # Unique identifier for this device
    RECORD_TAGS: List[str] = ["Generic Tag"]
    DEFAULT_RECORD_DESCRIPTION: str = (
        "No description set. Override `DEFAULT_RECORD_DESCRIPTION` in device settings."
    )

    ALLOWED_EXTENSIONS: Set[str] = set()
    ALLOWED_FOLDER_CONTENTS: Set[str] = set()  # e.g., {".odt", ".elid"}
    SESSION_TIMEOUT: int = 300
    POLL_SECONDS: float = 1.0

    def matches_file(self, filepath: str) -> bool:
        """Check if this device can process the given file."""
        path = Path(filepath)
        
        # Handle directories
        if path.is_dir():
            if self.ALLOWED_FOLDER_CONTENTS:
                contents = {f.suffix.lower() for f in path.rglob('*') if f.is_file()}
                return bool(contents.intersection(self.ALLOWED_FOLDER_CONTENTS))
            return False
        
        # Handle files - check extension
        return any(filepath.lower().endswith(ext) for ext in self.ALLOWED_EXTENSIONS)

    @classmethod
    def get_device_id(cls) -> str:
        """Get unique device identifier."""
        return cls.DEVICE_ID

