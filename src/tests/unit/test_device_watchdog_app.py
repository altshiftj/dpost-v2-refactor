import pytest
from unittest.mock import MagicMock, patch

# Import the DeviceWatchdogApp from your module.
from src.core.app.device_watchdog_app import DeviceWatchdogApp

# ------------------------
# Dummy Implementations
# ------------------------


class DummyUI:
    """A dummy UI implementation that satisfies the UserInterface interface."""

    def __init__(self):
        self.scheduled_tasks = []
        self.destroyed = False

    def schedule_task(self, interval_ms, callback):
        # For testing, record the task and return a dummy task id.
        self.scheduled_tasks.append((interval_ms, callback))
        return f"task_{len(self.scheduled_tasks)}"

    def set_close_handler(self, callback):
        self.close_handler = callback

    def set_exception_handler(self, callback):
        self.exception_handler = callback

    def show_error(self, title, message):
        self.error_shown = (title, message)

    def destroy(self):
        self.destroyed = True

    def run_main_loop(self):
        # Simulate a KeyboardInterrupt to test shutdown handling.
        raise KeyboardInterrupt

    def cancel_task(self, handle):
        # For testing, remove tasks that match the dummy handle.
        self.scheduled_tasks = [t for t in self.scheduled_tasks if t[0] != handle]

    def show_done_dialog(self, callback):
        # Record that a done dialog was shown with the provided callback.
        self.done_dialog_callback = callback


class DummySyncManager:
    """A dummy sync manager that satisfies the ISyncManager interface."""

    def __init__(self, ui):
        self.ui = ui
        self.synced_records = []
        self.logs_synced = 0

    def sync_record_to_database(self, local_record):
        self.synced_records.append(local_record)

    def sync_logs_to_database(self):
        self.logs_synced += 1


class DummyFileProcessor:
    """A dummy file processor that implements the minimal BaseFileProcessor methods."""

    def device_specific_preprocessing(self, src_path):
        # Simply return the input path.
        return src_path

    def is_valid_datatype(self, path):
        return True

    def is_appendable(self, record, filename_prefix, extension):
        return True

    def device_specific_processing(self, src_path, record_path, file_id, extension):
        # Return a dummy final path and a dummy datatype.
        return (f"{record_path}/dummy_file{extension}", "dummy_type")


# ------------------------
# Fixtures
# ------------------------


@pytest.fixture
def dummy_ui():
    return DummyUI()


@pytest.fixture
def dummy_sync_manager(dummy_ui):
    return DummySyncManager(ui=dummy_ui)


@pytest.fixture
def dummy_processor():
    return DummyFileProcessor()


@pytest.fixture
def app(dummy_ui, dummy_processor, dummy_sync_manager):
    # Patch the Observer so that no real thread is started.
    with patch("src.core.app.device_watchdog_app.Observer") as mock_observer:
        dummy_observer = MagicMock()
        mock_observer.return_value = dummy_observer
        # Create an instance of the app with dummy components.
        app_instance = DeviceWatchdogApp(
            ui=dummy_ui, sync_manager=dummy_sync_manager, file_processor=dummy_processor
        )
        # Store the dummy observer for later inspection.
        app_instance._dummy_observer = dummy_observer
        return app_instance


# ------------------------
# Tests
# ------------------------


def test_initialization(app, dummy_ui):
    """
    Verify that on initialization:
      - The watchdog observer is scheduled and started.
      - The UI has a task scheduled to call process_events.
      - The UI's close and exception handlers are set.
      - The session manager's end_session_callback is set to the app's end_session.
    """
    dummy_observer = app._dummy_observer
    dummy_observer.schedule.assert_called()  # Ensures schedule was called.
    dummy_observer.start.assert_called()  # Ensures observer.start() was called.

    # Check that the UI has at least one scheduled task (for process_events).
    assert len(dummy_ui.scheduled_tasks) >= 1

    # Check that close and exception handlers were set.
    assert hasattr(dummy_ui, "close_handler")
    assert hasattr(dummy_ui, "exception_handler")

    # Check that the session manager's callback is set.
    assert app.session_manager.end_session_callback == app.end_session


def test_process_events_empty_queue(app, dummy_ui):
    """
    When the event queue is empty, process_events should simply schedule the next iteration.
    Also, when log_sync_counter is 0 (or >=9000), sync_logs_to_database should be called.
    """
    # Ensure the event queue is empty.
    while not app.event_queue.empty():
        app.event_queue.get()
    initial_task_count = len(dummy_ui.scheduled_tasks)
    app.log_sync_counter = 0

    # Patch the sync_logs_to_database method to track its call.
    original_sync_logs = app.file_processing.sync_logs_to_database
    app.file_processing.sync_logs_to_database = MagicMock()

    # Call process_events.
    app.process_events()

    # A new task should have been scheduled.
    assert len(dummy_ui.scheduled_tasks) > initial_task_count

    # Verify that sync_logs_to_database was called.
    app.file_processing.sync_logs_to_database.assert_called_once()

    # Restore the original method.
    app.file_processing.sync_logs_to_database = original_sync_logs


def test_process_events_with_item(app):
    """
    If the event queue contains an item, process_events should dequeue it and pass it to file_processing.process_item.
    """
    test_path = "/path/to/test_file.tif"
    app.event_queue.put(test_path)

    # Patch process_item and sync_logs_to_database to prevent blocking.
    original_process_item = app.file_processing.process_item
    original_sync_logs = app.file_processing.sync_logs_to_database
    app.file_processing.process_item = MagicMock()
    app.file_processing.sync_logs_to_database = MagicMock()

    app.process_events()

    # Verify process_item was called with the test_path.
    app.file_processing.process_item.assert_called_with(test_path)

    # Restore the original methods.
    app.file_processing.process_item = original_process_item
    app.file_processing.sync_logs_to_database = original_sync_logs


def test_on_closing(app, dummy_ui):
    """
    Verify that on_closing ends an active session (if any), stops the observer, and destroys the UI.
    """
    # Set the session as active.
    app.session_manager.session_active = True
    # Patch session_manager.end_session to track its call.
    app.session_manager.end_session = MagicMock()

    # Patch observer's stop and join methods.
    dummy_observer = app._dummy_observer
    dummy_observer.stop = MagicMock()
    dummy_observer.join = MagicMock()

    app.on_closing()

    # Verify session_manager.end_session was called.
    app.session_manager.end_session.assert_called_once()
    # Verify observer.stop and join were called.
    dummy_observer.stop.assert_called_once()
    dummy_observer.join.assert_called_once()
    # Verify the UI is destroyed.
    assert dummy_ui.destroyed is True


def test_run_handles_keyboard_interrupt(app, dummy_ui):
    """
    Verify that if ui.run_main_loop() raises KeyboardInterrupt, on_closing is called.
    """
    app.on_closing = MagicMock()
    dummy_ui.run_main_loop = MagicMock(side_effect=KeyboardInterrupt)
    app.run()
    app.on_closing.assert_called_once()


def test_run_handles_exception(app, dummy_ui):
    """
    Verify that if ui.run_main_loop() raises a generic Exception, handle_exception is called.
    """
    app.handle_exception = MagicMock()
    dummy_ui.run_main_loop = MagicMock(side_effect=Exception("Test Exception"))
    app.run()
    app.handle_exception.assert_called_once()
