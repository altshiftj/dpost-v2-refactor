import pytest
from unittest.mock import MagicMock


def _drain_pending_tasks(ui, max_iterations: int = 10):
    for _ in range(max_iterations):
        if not ui.scheduled_tasks:
            break
        pending = list(ui.scheduled_tasks)
        ui.scheduled_tasks.clear()
        for _, cb in pending:
            cb()


def test_initialization(watchdog_app, fake_ui):
    watchdog_app.initialize()
    observer = watchdog_app.directory_observer

    interval_ms, callback = fake_ui.scheduled_tasks[0]
    callback()

    observer.schedule.assert_called_once()
    observer.start.assert_called_once()

    assert fake_ui.close_handler is not None
    assert fake_ui.exception_handler is not None
    assert (
        watchdog_app.session_manager.end_session_callback.__func__
        is watchdog_app.end_session.__func__
    )
    

def test_process_events_with_item(watchdog_app):
    watchdog_app.initialize()

    sample_path = "/tmp/MuS-ipat-sample.tif"
    watchdog_app.event_queue.put(sample_path)
    watchdog_app.file_processing.processed = []

    watchdog_app.process_events()

    assert sample_path in watchdog_app.file_processing.processed


def test_on_closing(watchdog_app, fake_ui):
    watchdog_app.session_manager.session_active = True
    watchdog_app.session_manager.end_session = MagicMock()

    observer = watchdog_app.directory_observer

    watchdog_app.on_closing()

    watchdog_app.session_manager.end_session.assert_called_once()
    observer.stop.assert_called_once()
    observer.join.assert_called_once()
    assert fake_ui.destroyed is True


def test_run_handles_keyboard_interrupt(watchdog_app, fake_ui):
    watchdog_app.on_closing = MagicMock()
    fake_ui.run_main_loop = MagicMock(side_effect=KeyboardInterrupt)

    watchdog_app.run()

    watchdog_app.on_closing.assert_called_once()


def test_run_handles_exception(watchdog_app, fake_ui):
    watchdog_app.handle_exception = MagicMock()
    fake_ui.run_main_loop = MagicMock(side_effect=Exception("boom"))

    watchdog_app.run()

    watchdog_app.handle_exception.assert_called_once()
