import pytest
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace

from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.core.config import init_config, reset_service, current
from ipat_watchdog.core.storage.filesystem_utils import init_dirs
from ipat_watchdog.device_plugins.test_device.settings import build_config as build_device_config
from ipat_watchdog.pc_plugins.test_pc.settings import build_config as build_pc_config

from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_processor import DummyProcessor
from tests.helpers.fake_handler import FakeFileEventHandler
from tests.helpers.fake_observer import FakeObserver
from tests.helpers.fake_session import FakeSessionManager
from tests.helpers.fake_process_manager import FakeFileProcessManager


@pytest.fixture
def config_service(tmp_path) -> init_config.__annotations__["return"]:
    """Initialise the configuration service with sandboxed paths for tests."""
    root: Path = tmp_path / "sandbox"
    overrides = {
        "app_dir": root / "App",
        "watch_dir": root / "Upload",
        "dest_dir": root / "Data",
        "rename_dir": root / "Data" / "00_To_Rename",
        "exceptions_dir": root / "Data" / "01_Exceptions",
        "daily_records_json": root / "records.json",
    }

    pc_config = build_pc_config(override_paths=overrides)
    pc_config = replace(pc_config, session=replace(pc_config.session, timeout_seconds=300))

    device_config = build_device_config()
    device_config = replace(
        device_config,
        session=replace(device_config.session, timeout_seconds=300),
        watcher=replace(
            device_config.watcher,
            poll_seconds=0.2,
            max_wait_seconds=10.0,
            stable_cycles=1,
        ),
    )

    service = init_config(pc_config, [device_config])
    init_dirs()
    yield service
    reset_service()


@pytest.fixture
def pc_paths(config_service):
    return config_service.pc.paths


@pytest.fixture
def device_config(config_service):
    return config_service.devices[0]


@pytest.fixture
def tmp_settings(config_service, pc_paths, device_config):
    log_file = pc_paths.app_dir / "watchdog.log"
    return SimpleNamespace(
        APP_DIR=pc_paths.app_dir,
        WATCH_DIR=pc_paths.watch_dir,
        DEST_DIR=pc_paths.dest_dir,
        RENAME_DIR=pc_paths.rename_dir,
        EXCEPTIONS_DIR=pc_paths.exceptions_dir,
        DAILY_RECORDS_JSON=pc_paths.daily_records_json,
        LOG_FILE=log_file,
        POLL_SECONDS=device_config.watcher.poll_seconds,
        STABLE_CYCLES=device_config.watcher.stable_cycles,
        MAX_WAIT_SECONDS=device_config.watcher.max_wait_seconds,
        SESSION_TIMEOUT=device_config.session.timeout_seconds,
        DEBOUNCE_TIME=0.1,
        SENTINEL_NAME=device_config.watcher.sentinel_name,
    )


@pytest.fixture
def active_config(config_service):
    return current()


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
def watchdog_app(config_service, fake_ui, fake_sync):
    init_dirs()
    return DeviceWatchdogApp(
        ui=fake_ui,
        sync_manager=fake_sync,
        config_service=config_service,
        session_manager_cls=FakeSessionManager,
        file_process_manager_cls=FakeFileProcessManager,
    )
