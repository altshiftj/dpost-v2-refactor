from ipat_watchdog.core.config.pc_settings import PCSettings
from ipat_watchdog.core.config.device_settings_base import DeviceSettings
import re

class DummyDeviceSettings(DeviceSettings):
    DEVICE_ID = 'dev1'
    DEVICE_TYPE = 'SEM'
    DEVICE_USER_KADI_ID = 'user123'
    ALLOWED_EXTENSIONS = {'.tiff', '.bmp'}
    FILENAME_PATTERN = re.compile(r'.*REM.*')
    
    def matches_file(self, filepath: str) -> bool:
        """Check if this device can process the given file - both pattern and extension."""
        from pathlib import Path
        path = Path(filepath)
        
        # Check if extension is allowed
        has_allowed_ext = any(filepath.lower().endswith(ext) for ext in self.ALLOWED_EXTENSIONS)
        
        # Check if filename matches pattern  
        matches_pattern = bool(self.FILENAME_PATTERN.search(path.name))
        
        return has_allowed_ext and matches_pattern


def test_global_settings_instantiation():
    gs = PCSettings()
    assert hasattr(gs, 'WATCH_DIR')
    assert hasattr(gs, 'DEST_DIR')
    assert hasattr(gs, 'SESSION_TIMEOUT')
    assert hasattr(gs, 'ID_SEP')
    assert hasattr(gs, 'FILENAME_PATTERN')
    assert hasattr(gs, 'POLL_SECONDS')


def test_device_settings_matches_file():
    ds = DummyDeviceSettings()
    assert ds.matches_file('REM_Test.tiff')
    assert not ds.matches_file('REM_Test.txt')
    assert not ds.matches_file('other.bmp')
    assert ds.matches_file('REM-Test.bmp')
