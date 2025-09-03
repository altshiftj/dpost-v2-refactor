from ipat_watchdog.core.config.global_settings import GlobalSettings
from ipat_watchdog.core.config.device_settings_base import DeviceSettings
import re

class DummyDeviceSettings(DeviceSettings):
    DEVICE_ID = 'dev1'
    DEVICE_TYPE = 'SEM'
    DEVICE_USER_KADI_ID = 'user123'
    ALLOWED_EXTENSIONS = {'.tiff', '.bmp'}
    FILENAME_PATTERN = re.compile(r'.*REM.*')


def test_global_settings_instantiation():
    gs = GlobalSettings()
    assert hasattr(gs, 'WATCH_DIR')
    assert hasattr(gs, 'DEST_DIR')
    assert hasattr(gs, 'DEBOUNCE_TIME')
    assert hasattr(gs, 'LOG_FILE')
    assert hasattr(gs, 'KADI_SERVER')
    assert hasattr(gs, 'KADI_TOKEN')


def test_device_settings_matches_file():
    ds = DummyDeviceSettings()
    assert ds.matches_file('REM_Test.tiff')
    assert not ds.matches_file('REM_Test.txt')
    assert not ds.matches_file('other.bmp')
    assert ds.matches_file('REM-Test.bmp')
