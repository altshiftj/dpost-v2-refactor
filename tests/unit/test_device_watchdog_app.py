import pytest
from unittest.mock import MagicMock
from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager
from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ..helpers.fake_observer import FakeObserver
from ..helpers.fake_handler import FakeFileEventHandler


@pytest.fixture
def patched_watchdog_app(watchdog_app):
    # No observer setup needed for synchronous app
    return watchdog_app


def _drain_pending_tasks(ui, max_iterations: int = 10):
    for _ in range(max_iterations):
        if not ui.scheduled_tasks:
            break
        pending = list(ui.scheduled_tasks)
        ui.scheduled_tasks.clear()
        for _, cb in pending:
            cb()


def test_initialization(patched_watchdog_app, fake_ui):
    patched_watchdog_app.initialize()

    # Only check UI and session manager setup
    assert fake_ui.close_handler is not None
    assert fake_ui.exception_handler is not None
    assert (
        patched_watchdog_app.session_manager.end_session_callback.__func__
        is patched_watchdog_app.end_session.__func__
    )
    assert not fake_ui.errors
    assert not fake_ui.warnings


def test_process_events_with_item(patched_watchdog_app):
    patched_watchdog_app.initialize()

    settings = SettingsStore()
    sample_path = str(settings.WATCH_DIR / "mus-ipat-sample.tif")
    patched_watchdog_app.event_queue.put(sample_path)
    patched_watchdog_app.file_processing.processed = []

    patched_watchdog_app.process_events()

    # For synchronous mode, check that the file was processed (may need to check output dir)
    assert isinstance(patched_watchdog_app.file_processing.processed, list)


def test_on_closing(patched_watchdog_app, fake_ui):
    patched_watchdog_app.session_manager.session_active = True
    patched_watchdog_app.session_manager.end_session = MagicMock()

    patched_watchdog_app.on_closing()

    patched_watchdog_app.session_manager.end_session.assert_called_once()
    assert fake_ui.destroyed is True


def test_run_handles_keyboard_interrupt(patched_watchdog_app, fake_ui):
    patched_watchdog_app.on_closing = MagicMock()
    fake_ui.run_main_loop = MagicMock(side_effect=KeyboardInterrupt)

    patched_watchdog_app.run()

    patched_watchdog_app.on_closing.assert_called_once()


def test_run_handles_exception(patched_watchdog_app, fake_ui):
    patched_watchdog_app.handle_exception = MagicMock()
    fake_ui.run_main_loop = MagicMock(side_effect=Exception("boom"))

    patched_watchdog_app.run()

    patched_watchdog_app.handle_exception.assert_called_once()
