# ruff: noqa: E402
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

# Ensure local source takes precedence so tests exercise workspace code, not installed package.
TESTS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_ROOT.parent
SRC_ROOT = PROJECT_ROOT / "src"
# Prepend src first to ensure local package imports resolve to workspace sources.
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
# Also add project root for any relative test package imports
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from dpost.application.config.context import current, init_config, reset_service
from dpost.application.runtime.device_watchdog_app import DeviceWatchdogApp
from dpost.device_plugins.test_device.settings import (
    build_config as build_device_config,
)
from dpost.infrastructure.storage.filesystem_utils import init_dirs
from dpost.pc_plugins.test_pc.settings import build_config as build_pc_config
from tests.helpers.fake_observer import FakeObserver
from tests.helpers.fake_process_manager import FakeFileProcessManager
from tests.helpers.fake_processor import DummyProcessor
from tests.helpers.fake_session import FakeSessionManager
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_ui import HeadlessUI


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Assign the `legacy` marker automatically for archived test paths."""
    for item in items:
        path_obj = Path(str(getattr(item, "path", item.fspath)))
        if "legacy" in path_obj.parts:
            item.add_marker(pytest.mark.legacy)


@pytest.fixture
def config_service(tmp_path):
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
    pc_config.session.timeout_seconds = 300

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
    init_dirs([str(path) for path in current().directory_list])
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
def fake_session_manager():
    return FakeSessionManager


@pytest.fixture
def fake_file_process_manager():
    return FakeFileProcessManager


@pytest.fixture
def watchdog_app(config_service, fake_ui, fake_sync):
    init_dirs([str(path) for path in current().directory_list])
    observer_stub = FakeObserver()
    app = DeviceWatchdogApp(
        ui=fake_ui,
        sync_manager=fake_sync,
        config_service=config_service,
        session_manager_cls=cast(Any, FakeSessionManager),
        file_process_manager_cls=cast(Any, FakeFileProcessManager),
        observer_factory=lambda: observer_stub,
    )
    cast(Any, app)._observer_stub = observer_stub
    return app
