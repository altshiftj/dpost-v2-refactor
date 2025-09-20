import pytest
from pathlib import Path
from unittest.mock import MagicMock

from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp


@pytest.fixture
def patched_watchdog_app(watchdog_app):
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

    watch_dir = Path(patched_watchdog_app.watch_dir)
    watch_dir.mkdir(parents=True, exist_ok=True)
    sample_path = watch_dir / "mus-ipat-sample.tif"
    sample_path.write_text("data")

    patched_watchdog_app.event_queue.put(str(sample_path))
    patched_watchdog_app.file_processing.processed = []

    patched_watchdog_app.process_events()

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
