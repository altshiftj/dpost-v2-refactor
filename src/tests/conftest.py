# core/tests/conftest.py
import threading
from pathlib import Path
import pytest

from config.settings_store import SettingsStore
from config.settings_base import BaseSettings
from app.device_watchdog_app import DeviceWatchdogApp

from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_processor import DummyProcessor
from tests.helpers.fake_handler import FakeFileEventHandler
from tests.helpers.fake_observer import FakeObserver
from tests.helpers.fake_session import FakeSessionManager
from tests.helpers.fake_process_manager import FakeFileProcessManager

# ───────────────────────────────────────── fixtures ──────────────────────────

@pytest.fixture(autouse=True)
def _reset_settings_store():
    """Ensure SettingsStore is blank between tests."""
    yield
    SettingsStore.reset()


@pytest.fixture
def tmp_settings(tmp_path) -> BaseSettings:
    """
    Device‑agnostic settings object that points every directory at tmp_path.
    """
    class _TmpSettings(BaseSettings):
        # Directories
        WATCH_DIR = tmp_path / "Upload_Ordner"
        DEST_DIR = tmp_path / "Data"
        RENAME_DIR = tmp_path / "Data" / "00_To_Rename"
        EXCEPTIONS_DIR = tmp_path / "Data" / "01_Exceptions"
        DAILY_RECORDS_JSON = tmp_path / "records.json"
        LOG_FILE = tmp_path / "watchdog.log"

        # Session / Sync
        SESSION_TIMEOUT = 5
        SYNC_LOGS = True
        LOG_SYNC_INTERVAL = 1

        # File rules
        ALLOWED_EXTENSIONS = {".tif", ".tiff", ".txt"}
        DEBOUNCE_TIME = 1

        # Filename & ID
        ID_SEP = "-"
        FILE_SEP = "_"
        DEVICE_TYPE = "TEST"
        FILENAME_PATTERN = BaseSettings.FILENAME_PATTERN

        # Record metadata
        DEVICE_USER_KADI_ID = "test-user"
        DEVICE_USER_PERSISTENT_ID = 1
        DEVICE_RECORD_PERSISTENT_ID = 999
        RECORD_TAGS = ["TestTag"]
        DEFAULT_RECORD_DESCRIPTION = "Test record"

    SettingsStore.set(_TmpSettings())
    return SettingsStore.get()


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
    fake_file_process_manager
):
    app = DeviceWatchdogApp(
        ui=fake_ui,
        sync_manager=fake_sync,
        file_processor=dummy_processor,
        observer_cls=lambda: fake_observer,
        file_event_handler_cls=fake_handler,
        session_manager_cls=fake_session_manager,
        file_process_manager_cls=fake_file_process_manager,
    )
    app.directory_observer = fake_observer  # for assertions
    return app