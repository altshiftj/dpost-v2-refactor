import pytest
from unittest.mock import MagicMock
from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager
from ipat_watchdog.pc_plugins.test_pc.settings import TestPCSettings
from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp


@pytest.fixture
def patched_watchdog_app(watchdog_app, tmp_settings):
    # Create a settings manager with the tmp_settings as device settings
    global_settings = TestPCSettings()
    settings_manager = SettingsManager(
        available_devices=[tmp_settings],
        pc_settings=global_settings
    )
    SettingsStore.set_manager(settings_manager)
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
    observer = patched_watchdog_app.directory_observer

    interval_ms, callback = fake_ui.scheduled_tasks[0]
    callback()

    observer.schedule.assert_called_once()
    observer.start.assert_called_once()

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

    assert sample_path in patched_watchdog_app.file_processing.processed


def test_on_closing(patched_watchdog_app, fake_ui):
    patched_watchdog_app.session_manager.session_active = True
    patched_watchdog_app.session_manager.end_session = MagicMock()

    observer = patched_watchdog_app.directory_observer

    patched_watchdog_app.on_closing()

    patched_watchdog_app.session_manager.end_session.assert_called_once()
    observer.stop.assert_called_once()
    observer.join.assert_called_once()
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
