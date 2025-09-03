from ipat_watchdog.core.config.settings_store import SettingsManager
from ipat_watchdog.core.config.global_settings import GlobalSettings
from ipat_watchdog.core.config.device_settings_base import DeviceSettings
from ipat_watchdog.device_plugins.sem_tischrem_blb.settings import TischREMSettings
import re

class DummyDeviceSettings(DeviceSettings):
    DEVICE_ID = 'dev1'
    DEVICE_TYPE = 'SEM'
    DEVICE_USER_KADI_ID = 'user123'
    ALLOWED_EXTENSIONS = {'.tiff', '.bmp'}
    FILENAME_PATTERN = re.compile(r'.*REM.*')

class DummyDeviceSettings2(DeviceSettings):
    DEVICE_ID = 'dev2'
    DEVICE_TYPE = 'UTM'
    DEVICE_USER_KADI_ID = 'user456'
    ALLOWED_EXTENSIONS = {'.tiff'}
    FILENAME_PATTERN = re.compile(r'.*Test.*')

def test_settings_manager_basic():
    gs = GlobalSettings()
    sm = SettingsManager(gs)
    assert sm.global_settings is gs
    assert sm.get_all_devices() == []

    dev1 = DummyDeviceSettings()
    dev2 = DummyDeviceSettings2()
    sm.register_device(dev1)
    sm.register_device(dev2)
    assert sm.get_device_settings('dev1') is dev1
    assert sm.get_device_settings('dev2') is dev2
    assert len(sm.get_all_devices()) == 2

    compatible = sm.find_compatible_devices('REM_Test.tiff')
    assert dev1 in compatible
    assert dev2 in compatible
    compatible2 = sm.find_compatible_devices('REM_Test.bmp')
    assert dev1 in compatible2
    assert dev2 not in compatible2

def test_settings_manager_with_real_device():
    """Test that real device settings work with SettingsManager"""
    gs = GlobalSettings()
    sm = SettingsManager(gs)
    
    tischrem_settings = TischREMSettings()
    sm.register_device(tischrem_settings)
    
    # Should be registered with its DEVICE_ID
    retrieved = sm.get_device_settings('sem_tischrem_blb')
    assert retrieved is tischrem_settings
    
    # Should match .tiff files with proper filename format
    compatible = sm.find_compatible_devices('jfi-ipat-test.tiff')
    assert tischrem_settings in compatible
    
    # Should not match .txt files
    compatible2 = sm.find_compatible_devices('jfi-ipat-test.txt')
    assert tischrem_settings not in compatible2
