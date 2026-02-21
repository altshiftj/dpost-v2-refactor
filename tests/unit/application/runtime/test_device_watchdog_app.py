import queue
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dpost.application.processing import ProcessingResult, ProcessingStatus
from dpost.application.runtime.device_watchdog_app import (
    DeviceWatchdogApp,
    QueueingEventHandler,
)



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


def test_start_observer_is_noop_when_already_started(watchdog_app):
    watchdog_app.initialize()
    observer = watchdog_app._observer_stub

    watchdog_app._start_observer()

    observer.schedule.assert_called_once()
    observer.start.assert_called_once()


def test_stop_observer_is_noop_without_observer(watchdog_app):
    watchdog_app.observer = None
    watchdog_app.event_handler = None

    watchdog_app._stop_observer()

    assert watchdog_app.observer is None
    assert watchdog_app.event_handler is None


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


def test_modified_events_queue_only_when_callback_allows():
    event_queue = queue.Queue()
    handler = QueueingEventHandler(
        event_queue,
        should_queue_modified=lambda path: path.endswith(".csv"),
    )

    class DummyEvent:
        def __init__(self, src_path: str):
            self.src_path = src_path
            self.is_directory = False

    handler.on_modified(DummyEvent("C:/tmp/changed.csv"))
    assert event_queue.get_nowait() == "C:/tmp/changed.csv"

    handler.on_modified(DummyEvent("C:/tmp/changed.txt"))
    assert event_queue.empty()


def test_modified_event_handler_on_created_and_guard_paths():
    event_queue = queue.Queue()

    class DummyEvent:
        def __init__(self, src_path: str, is_directory: bool = False):
            self.src_path = src_path
            self.is_directory = is_directory

    handler = QueueingEventHandler(event_queue)
    handler.on_created(DummyEvent("C:/tmp/new-folder", is_directory=True))
    assert event_queue.get_nowait() == "C:/tmp/new-folder"

    handler.on_modified(DummyEvent("C:/tmp/dir", is_directory=True))
    assert event_queue.empty()

    handler.on_modified(DummyEvent("C:/tmp/no-callback.txt"))
    assert event_queue.empty()


def test_modified_event_handler_swallows_callback_errors():
    event_queue = queue.Queue()
    handler = QueueingEventHandler(
        event_queue,
        should_queue_modified=lambda _path: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    class DummyEvent:
        def __init__(self, src_path: str):
            self.src_path = src_path
            self.is_directory = False

    handler.on_modified(DummyEvent("C:/tmp/changed.csv"))

    assert event_queue.empty()


def test_handle_processing_result_schedules_retry_with_default_delay(
    watchdog_app, monkeypatch
):
    scheduled = []
    monkeypatch.setattr(watchdog_app, "_default_retry_delay", lambda: 2.5)
    monkeypatch.setattr(
        watchdog_app, "_schedule_retry", lambda path, delay: scheduled.append((path, delay))
    )
    result = ProcessingResult(status=ProcessingStatus.DEFERRED, message="wait")

    watchdog_app._handle_processing_result("C:/tmp/retry.txt", result)

    assert scheduled == [("C:/tmp/retry.txt", 2.5)]


def test_handle_processing_result_ignores_none_result(watchdog_app, monkeypatch):
    called = {"scheduled": False}
    monkeypatch.setattr(
        watchdog_app, "_schedule_retry", lambda _path, _delay: called.__setitem__("scheduled", True)
    )

    watchdog_app._handle_processing_result("C:/tmp/retry.txt", None)

    assert called["scheduled"] is False


def test_default_retry_delay_falls_back_on_invalid_config(watchdog_app):
    watchdog_app.config_service.pc.watcher.retry_delay_seconds = "invalid"
    assert watchdog_app._default_retry_delay() == 2.0


def test_enqueue_if_present_requeues_existing_and_skips_missing(watchdog_app, tmp_path: Path):
    existing = tmp_path / "exists.txt"
    existing.write_text("data")

    watchdog_app._enqueue_if_present(str(existing))
    assert watchdog_app.event_queue.get_nowait() == str(existing)

    watchdog_app._enqueue_if_present(str(tmp_path / "missing.txt"))
    assert watchdog_app.event_queue.empty()
