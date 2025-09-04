# tests/conftest.py
import pytest
from pathlib import Path

import dotenv
dotenv.load_dotenv()

from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager
from ipat_watchdog.core.config.settings_base import BaseSettings
from ipat_watchdog.core.config.device_settings_base import DeviceSettings
from ipat_watchdog.core.config.global_settings import PCSettings
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
    """Create a fake settings manager for tests."""
    global_settings = PCSettings()
    # Copy any attributes from tmp_settings to global_settings
    for attr_name in dir(tmp_settings):
        if not attr_name.startswith('_') and hasattr(global_settings, attr_name):
            setattr(global_settings, attr_name, getattr(tmp_settings, attr_name))
    
    settings_manager = SettingsManager(global_settings)
    SettingsStore.set_manager(settings_manager)
    return settings_manager

@pytest.fixture(autouse=True)
def _reset_settings_store():
    yield
    SettingsStore.reset()           # leaves prod global state untouched


@pytest.fixture
def tmp_settings(tmp_path) -> DeviceSettings:
    """Return a settings instance whose entire file-tree lives in tmp_path."""
    root: Path = tmp_path / "sandbox"

    class TestSettings(DeviceSettings):
        # ─ snapshot-watcher tweaks ─
        POLL_SECONDS = 0.2
        STABLE_CYCLES = 1
        MAX_WAIT_SECONDS = 10.0

        ALLOWED_EXTENSIONS = {".tif", ".txt"}
        
        # ─ Additional required attributes ─
        ID_SEP = '-'
        DEVICE_TYPE = 'TEST'
        DEVICE_RECORD_KADI_ID = 'test_01'
        SENTINEL_NAME = None  # Can be overridden by individual tests
        SESSION_TIMEOUT = 300
        DEBOUNCE_TIME = 0.1

        # ─ filesystem layout ─
        APP_DIR       = root / "App"
        WATCH_DIR     = root / "Upload_Ordner"
        DEST_DIR      = root / "Data"
        RENAME_DIR    = DEST_DIR / "00_To_Rename"
        EXCEPTIONS_DIR = DEST_DIR / "01_Exceptions"
        DAILY_RECORDS_JSON = root / "records.json"
        LOG_FILE            = root / "watchdog.log"

        # DeviceSettings requirements
        @classmethod
        def get_device_id(cls) -> str:
            return "test_device"
            
        def matches_file(self, filepath: str) -> bool:
            """Check if this device can process the given file."""
            from pathlib import Path
            path = Path(filepath)
            return path.suffix.lower() in {'.tif', '.txt'}

        # automatically create dirs when instantiated
        def __post_init__(self):
            for d in (
                self.WATCH_DIR,
                self.DEST_DIR,
                self.RENAME_DIR,
                self.EXCEPTIONS_DIR,
            ):
                d.mkdir(parents=True, exist_ok=True)

    settings = TestSettings()
    SettingsStore.set_manager(SettingsManager(PCSettings(), [settings]))  # use new API
    return settings


@pytest.fixture
def fake_ui():
    return HeadlessUI()


@pytest.fixture
def fake_sync(fake_ui):
    return DummySyncManager(ui=fake_ui)


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
    dummy_processor,
    fake_observer,
    fake_handler,
    fake_session_manager,
    fake_file_process_manager,
    fake_settings_manager
):
    app = DeviceWatchdogApp(
        ui=fake_ui,
        sync_manager=fake_sync,
        settings_manager=fake_settings_manager,
        observer_cls=lambda: fake_observer,
        file_event_handler_cls=fake_handler,
        session_manager_cls=fake_session_manager,
        file_process_manager_cls=fake_file_process_manager,
    )
    app.directory_observer = fake_observer  # for assertions
    return app