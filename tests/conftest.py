# tests/conftest.py
import pytest
from pathlib import Path

import dotenv
dotenv.load_dotenv()

from ipat_watchdog.core.config.settings_store import SettingsStore
from ipat_watchdog.core.config.settings_base import BaseSettings
from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp

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
    yield
    SettingsStore.reset()           # leaves prod global state untouched


@pytest.fixture
def tmp_settings(tmp_path) -> BaseSettings:
    """Return a settings instance whose entire file-tree lives in tmp_path."""
    root: Path = tmp_path / "sandbox"

    class TestSettings(BaseSettings):
        # ─ snapshot-watcher tweaks ─
        POLL_SECONDS = 0.2
        STABLE_CYCLES = 1
        MAX_WAIT_SECONDS = 10.0

        ALLOWED_EXTENSIONS = {".tif", ".txt"}
        ALLOWED_FOLDER_CONTENTS = {".odt", ".elid"}

        # ─ filesystem layout ─
        APP_DIR       = root / "App"
        WATCH_DIR     = root / "Upload_Ordner"
        DEST_DIR      = root / "Data"
        RENAME_DIR    = DEST_DIR / "00_To_Rename"
        EXCEPTIONS_DIR = DEST_DIR / "01_Exceptions"
        DAILY_RECORDS_JSON = root / "records.json"
        LOG_FILE            = root / "watchdog.log"

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
    SettingsStore.set(settings)      # make the instance discoverable
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