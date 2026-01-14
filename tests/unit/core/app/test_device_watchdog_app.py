import queue
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp, QueueingEventHandler


def test_initialization_sets_handlers_and_starts_observer(watchdog_app, fake_ui):
    watchdog_app.initialize()

    close_handler = fake_ui.close_handler
    exception_handler = fake_ui.exception_handler

    assert close_handler.__self__ is watchdog_app
    assert close_handler.__func__ is DeviceWatchdogApp.on_closing
    assert exception_handler.__self__ is watchdog_app
    assert exception_handler.__func__ is DeviceWatchdogApp.handle_exception

    observer = watchdog_app._observer_stub
    observer.schedule.assert_called_once()
    observer.start.assert_called_once()
    assert watchdog_app.observer is observer


def test_process_events_with_item(watchdog_app, fake_ui):
    watchdog_app.initialize()

    watch_dir = Path(watchdog_app.watch_dir)
    watch_dir.mkdir(parents=True, exist_ok=True)
    sample_path = watch_dir / "mus-ipat-sample.tif"
    sample_path.write_text("data")

    watchdog_app.event_queue.put(str(sample_path))
    watchdog_app.file_processing.processed.clear()

    watchdog_app.process_events()

    assert watchdog_app.file_processing.processed == [str(sample_path)]
    assert fake_ui.scheduled_tasks  # rescheduled future poll


def test_process_events_handles_empty_queue_gracefully(watchdog_app, fake_ui):
    watchdog_app.process_events()

    assert watchdog_app._event_poll_handle == 1
    scheduled_callback = fake_ui.scheduled_tasks[-1][1]
    assert scheduled_callback.__self__ is watchdog_app
    assert scheduled_callback.__func__ is DeviceWatchdogApp.process_events


def test_process_events_surfaces_rejections(watchdog_app, fake_ui):
    watchdog_app.file_processing._rejected = [("/tmp/rejected.tif", "Unsupported extension")]

    watchdog_app.process_events()

    assert fake_ui.errors
    title, message = fake_ui.errors[-1]
    assert "Unsupported Input" in title
    assert "Unsupported extension" in message


def test_on_closing_stops_observer_and_destroys_ui(watchdog_app, fake_ui):
    watchdog_app.initialize()
    watchdog_app.session_manager.session_active = False

    watchdog_app.on_closing()

    observer = watchdog_app._observer_stub
    observer.stop.assert_called_once()
    observer.join.assert_called_once()
    assert fake_ui.destroyed is True


@pytest.mark.parametrize(
    "side_effect", [KeyboardInterrupt, RuntimeError("boom")], ids=["keyboard_interrupt", "generic_exception"]
)
def test_run_handles_ui_exceptions(watchdog_app, fake_ui, side_effect):
    if side_effect is KeyboardInterrupt:
        watchdog_app.on_closing = MagicMock()
        expected = watchdog_app.on_closing
    else:
        watchdog_app.handle_exception = MagicMock()
        expected = watchdog_app.handle_exception

    fake_ui.run_main_loop = MagicMock(side_effect=side_effect)

    watchdog_app.run()

    expected.assert_called_once()


def test_modified_events_are_queued():
    event_queue = queue.Queue()
    handler = QueueingEventHandler(event_queue)

    class DummyEvent:
        def __init__(self, src_path: str):
            self.src_path = src_path
            self.is_directory = False

    handler.on_modified(DummyEvent("C:/tmp/changed.csv"))

    assert not event_queue.empty()
    assert event_queue.get_nowait() == "C:/tmp/changed.csv"
