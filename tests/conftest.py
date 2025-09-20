# tests/conftest.py
import pytest
from pathlib import Path

import dotenv
dotenv.load_dotenv()

from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager
from ipat_watchdog.core.config.device_settings_base import DeviceSettings
from ipat_watchdog.core.config.pc_settings import PCSettings
from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp

from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_processor import DummyProcessor
from tests.helpers.fake_handler import FakeFileEventHandler
from tests.helpers.fake_observer import FakeObserver
from tests.helpers.fake_session import FakeSessionManager
from tests.helpers.fake_process_manager import FakeFileProcessManager

# ───────────────────────────────────────── fixtures ──────────────────────────

@pytest.fixture
def fake_settings_manager(tmp_settings):
    """Create a fake settings manager for tests using test PC plugin."""
    from ipat_watchdog.pc_plugins.test_pc.plugin import TestPCPlugin
    
    # Get the path overrides from tmp_settings
    path_overrides = {
        attr: getattr(tmp_settings, attr) for attr in [
            'APP_DIR', 'WATCH_DIR', 'DEST_DIR', 'RENAME_DIR', 
            'EXCEPTIONS_DIR', 'DAILY_RECORDS_JSON', 'LOG_FILE'
        ] if hasattr(tmp_settings, attr)
    }
    
    # Create test PC plugin with the same path overrides
    test_pc_plugin = TestPCPlugin(override_paths=path_overrides)
    pc_settings = test_pc_plugin.get_settings()
    
    settings_manager = SettingsManager(
        available_devices=[tmp_settings],
        pc_settings=pc_settings
    )
    SettingsStore.set_manager(settings_manager)
    return settings_manager

@pytest.fixture(autouse=True)
def _reset_settings_store():
    yield
    SettingsStore.reset()           # leaves prod global state untouched


@pytest.fixture
def tmp_settings(tmp_path) -> DeviceSettings:
    """Return a settings instance whose entire file-tree lives in tmp_path."""
    from ipat_watchdog.device_plugins.test_device.settings import TestDeviceSettings
    from ipat_watchdog.pc_plugins.test_pc.plugin import TestPCPlugin
    from pathlib import Path
    
    root: Path = tmp_path / "sandbox"

    # Create path overrides for both device and PC settings
    path_overrides = {
        'APP_DIR': root / "App",
        'WATCH_DIR': root / "Upload",
        'DEST_DIR': root / "Data", 
        'RENAME_DIR': root / "Data" / "00_To_Rename",
        'EXCEPTIONS_DIR': root / "Data" / "01_Exceptions",
        'DAILY_RECORDS_JSON': root / "records.json",
        'LOG_FILE': root / "watchdog.log"
    }

    # Create test PC plugin with path overrides
    test_pc_plugin = TestPCPlugin(override_paths=path_overrides)
    pc_settings = test_pc_plugin.get_settings()
    
    # Create a test device settings instance with the same path overrides
    settings = TestDeviceSettings()
    
    # Override paths to use temporary directory
    for key, value in path_overrides.items():
        setattr(settings, key, value)  # Force set even if attribute doesn't exist yet
    
    # Override for faster testing
    settings.POLL_SECONDS = 0.2
    settings.STABLE_CYCLES = 1
    settings.MAX_WAIT_SECONDS = 10.0
    settings.SESSION_TIMEOUT = 300
    settings.DEBOUNCE_TIME = 0.1
    settings.SENTINEL_NAME = None  # Can be overridden by individual tests

    # Automatically create dirs when instantiated
    for d in (
        settings.WATCH_DIR,
        settings.DEST_DIR,
        settings.RENAME_DIR,
        settings.EXCEPTIONS_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)

    SettingsStore.set_manager(SettingsManager(available_devices=[settings], pc_settings=pc_settings))
    return settings


@pytest.fixture
def fake_ui():
    return HeadlessUI()


@pytest.fixture
def fake_sync(fake_ui):
    return DummySyncManager(fake_ui)


@pytest.fixture
def dummy_processor():
    return DummyProcessor()


@pytest.fixture
def fake_observer():
    return FakeObserver()


@pytest.fixture
def fake_handler():
    return FakeFileEventHandler


@pytest.fixture
def fake_session_manager():
    return FakeSessionManager


@pytest.fixture
def fake_file_process_manager():
    return FakeFileProcessManager


@pytest.fixture
def watchdog_app(
    tmp_settings,
    fake_ui,
    fake_sync,
    fake_settings_manager
):
    app = DeviceWatchdogApp(
        ui=fake_ui,
        sync_manager=fake_sync,
        settings_manager=fake_settings_manager,
    )
    return app
