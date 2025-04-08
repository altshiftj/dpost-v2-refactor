from pathlib import Path
import tkinter as tk
import pytest
from unittest.mock import MagicMock
from src.processing.file_process_manager import FileProcessManager, BaseFileProcessor
from src.records.local_record import LocalRecord
from src.records.id_generator import IdGenerator


# --- Fixture to disable real I/O operations ---

@pytest.fixture(autouse=True)
def prevent_filesystem_writes(monkeypatch):
    # Block filesystem modifications
    monkeypatch.setattr("pathlib.Path.mkdir", lambda *args, **kwargs: None)
    monkeypatch.setattr("os.rename", lambda *args, **kwargs: None)
    monkeypatch.setattr("shutil.move", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.records.record_persistence.save_persisted_records", lambda x: None)


# --- Dummy classes to simulate dependencies ---

class DummyFileProcessor(BaseFileProcessor):
    def __init__(self, valid_datatype=True, appendable=True):
        self.valid_datatype = valid_datatype
        self.appendable = appendable

    def device_specific_preprocessing(self, src_path: str) -> str:
        return src_path

    def is_valid_datatype(self, path: str) -> bool:
        return self.valid_datatype

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        return self.appendable

    def device_specific_processing(self, src_path, record_path, file_id, extension):
        final_path = str(Path(record_path) / f"{file_id}{extension}")
        return final_path, "dummy_datatype"

class DummyUI:
    def __init__(self):
        self.calls = {
            "show_warning": [],
            "show_info": [],
            "show_error": [],
            "prompt_rename": [],
            "prompt_append_record": []
        }
        self.prompt_rename_return = None
        self.prompt_append_record_return = None

    def show_warning(self, title, message):
        self.calls["show_warning"].append((title, message))

    def show_info(self, title, message):
        self.calls["show_info"].append((title, message))

    def show_error(self, title, message):
        self.calls["show_error"].append((title, message))

    def prompt_rename(self):
        self.calls["prompt_rename"].append("called")
        return self.prompt_rename_return

    def prompt_append_record(self, record_name):
        self.calls["prompt_append_record"].append(record_name)
        return self.prompt_append_record_return

    def schedule_task(self, interval_ms, callback):
        callback()
        return 1

    def cancel_task(self, handle):
        pass

    def set_close_handler(self, callback):
        self.close_handler = callback

    def set_exception_handler(self, callback):
        self.exception_handler = callback

    def get_root(self):
        root = tk.Tk()
        root.withdraw()
        return root

class DummySessionManager:
    def __init__(self):
        self.session_active = False
        self.start_session_called = False
        self.reset_timer_called = False

    def start_session(self):
        self.start_session_called = True
        self.session_active = True

    def reset_timer(self):
        self.reset_timer_called = True

class DummyRecordManager:
    def __init__(self):
        self.records = {}

    def all_records_uploaded(self):
        return all(record.all_files_uploaded() for record in self.records.values())

    def get_record_by_id(self, record_id):
        return self.records.get(record_id)

    def create_record(self, filename_prefix):
        record_id = IdGenerator.generate_record_id(filename_prefix)
        new_record = LocalRecord(identifier=record_id)
        self.records[record_id] = new_record
        return new_record

    def add_item_to_record(self, path, record):
        record.files_uploaded[path] = True

    def sync_records_to_database(self):
        self.synced = True

    def sync_logs_to_database(self):
        self.logs_synced = True

class DummySyncManager:
    pass


# --- Fixture for FileProcessManager instance ---

@pytest.fixture
def fpm():
    ui = DummyUI()
    session_manager = DummySessionManager()
    sync_manager = DummySyncManager()
    file_processor = DummyFileProcessor(valid_datatype=True, appendable=True)
    manager = FileProcessManager(
        ui=ui,
        sync_manager=sync_manager,
        session_manager=session_manager,
        file_processor=file_processor
    )
    manager.records = DummyRecordManager()
    return manager

# --- Test cases ---

def test_init_triggers_sync_if_records_pending(monkeypatch):
    class DummyRecordManagerWithPending:
        def __init__(self):
            self.synced = False

        def all_records_uploaded(self):
            return False  # Trigger sync

        def sync_records_to_database(self):
            self.synced = True

        def sync_logs_to_database(self):
            pass

    ui = DummyUI()
    session_manager = DummySessionManager()
    sync_manager = DummySyncManager()
    file_processor = DummyFileProcessor()

    monkeypatch.setattr("src.processing.file_process_manager.RecordManager", lambda sync_manager: DummyRecordManagerWithPending())

    fpm = FileProcessManager(
        ui=ui,
        sync_manager=sync_manager,
        session_manager=session_manager,
        file_processor=file_processor
    )

    assert fpm.records.synced is True


def test_process_item_invalid_datatype(fpm, monkeypatch):
    # Simulate an invalid data type.
    fpm.file_processor.valid_datatype = False
    test_path = "/fake/path/invalid.txt"
    
    move_exception_called = False
    def fake_move_to_exception_folder(src, prefix, ext):
        nonlocal move_exception_called
        move_exception_called = True
    monkeypatch.setattr(
        "src.processing.file_process_manager.StorageManager.move_to_exception_folder",
        fake_move_to_exception_folder
    )
    
    fpm.process_item(test_path)
    # Verify that a warning was shown.
    assert len(fpm.ui.calls["show_warning"]) > 0
    # Verify that the exception folder move was triggered.
    assert move_exception_called
    # No record should have been created.
    assert len(fpm.records.records) == 0

def test_process_item_valid_new_record(fpm, monkeypatch):
    # Simulate a valid file with no existing record.
    fpm.file_processor.valid_datatype = True
    test_path = "/fake/path/ABC-DEF-sample.txt"
    # Patch PathManager.get_record_path to return a dummy path.
    monkeypatch.setattr(
        "src.processing.file_process_manager.PathManager.get_record_path",
        lambda prefix: "dummy_record_path"
    )
    fpm.process_item(test_path)
    expected_record_id = IdGenerator.generate_record_id("abc-def-sample")
    # Check that a new record was created.
    assert expected_record_id in fpm.records.records
    # Verify that the session was started.
    assert fpm.session_manager.start_session_called

def test_append_to_synced_record_confirm(fpm, monkeypatch):
    # Create an existing record that is fully synced.
    prefix = "ABC-DEF-sample"
    record_id = IdGenerator.generate_record_id(prefix.lower())
    record = LocalRecord(identifier=record_id)
    record.is_in_db = True
    record.files_uploaded = {"/fake/path/file": True}
    fpm.records.records[record_id] = record
    
    fpm.file_processor.appendable = True
    # Set the prompt to confirm appending.
    fpm.ui.prompt_append_record_return = True
    
    add_item_called = False
    original_add_item = fpm.add_item_to_record
    def fake_add_item(record_arg, src_path, filename_prefix, extension, notify=True):
        nonlocal add_item_called
        add_item_called = True
        original_add_item(record_arg, src_path, filename_prefix, extension, notify)
    monkeypatch.setattr(fpm, "add_item_to_record", fake_add_item)
    
    fpm._handle_append_to_synced_record(record, "/fake/path/ABC-DEF-sample.txt", prefix, ".txt")
    # Verify that prompt_append_record was called with the correct prefix.
    assert fpm.ui.calls["prompt_append_record"][0] == prefix
    # Verify that add_item_to_record was called.
    assert add_item_called

def test_append_to_synced_record_decline(fpm, monkeypatch):
    # Create an existing record that is fully synced.
    prefix = "ABC-DEF-sample"
    record_id = IdGenerator.generate_record_id(prefix.lower())
    record = LocalRecord(identifier=record_id)
    record.is_in_db = True
    record.files_uploaded = {"/fake/path/file": True}
    fpm.records.records[record_id] = record
    
    fpm.file_processor.appendable = True
    # Set the prompt to decline appending.
    fpm.ui.prompt_append_record_return = False
    # Simulate a valid rename response.
    fpm.ui.prompt_rename_return = {"name": "ABC", "institute": "DEF", "sample_ID": "sample"}
    
    route_called = False
    def fake_route_item(src_path, filename_prefix, extension):
        nonlocal route_called
        route_called = True
    monkeypatch.setattr(fpm, "_route_item", fake_route_item)
    
    fpm._handle_append_to_synced_record(record, "/fake/path/ABC-DEF-sample.txt", prefix, ".txt")
    # Verify that prompt_rename was called.
    assert len(fpm.ui.calls["prompt_rename"]) > 0
    # Verify that the _route_item method was eventually called.
    assert route_called


def test_invalid_filename_triggers_prompt(fpm, monkeypatch):
    test_path = "/fake/path/invalid--name.txt"

    # Force sanitize_and_validate to return is_valid_format = False
    monkeypatch.setattr(
        "src.processing.file_process_manager.FilenameValidator.sanitize_and_validate",
        lambda prefix: ("sanitized-invalid--name", False)
    )

    # Mock prompt rename to simulate user cancel
    fpm.ui.prompt_rename_return = {"name": "ABC", "institute": "DEF", "sample_ID": "sample"}

    rename_called = False
    def fake_prompt_item_rename(src_path, prefix, ext, **kwargs):
        nonlocal rename_called
        rename_called = True
    monkeypatch.setattr(fpm, "_prompt_item_rename", fake_prompt_item_rename)

    fpm.process_item(test_path)

    assert rename_called


def test_rename_cancellation_moves_file(fpm, monkeypatch):
    test_path = "/fake/path/ABC-DEF-cancel.txt"
    prefix = "ABC-DEF-cancel"
    extension = ".txt"

    # Simulate user cancelling the rename dialog
    fpm.ui.prompt_rename_return = None

    move_called = False
    def fake_move_to_rename_folder(src, pfx, ext):
        nonlocal move_called
        move_called = True
    monkeypatch.setattr(
        "src.processing.file_process_manager.StorageManager.move_to_rename_folder",
        fake_move_to_rename_folder
    )

    fpm._prompt_item_rename(test_path, prefix, extension)

    assert move_called
    assert fpm.ui.calls["show_info"][-1][0] == "Operation Cancelled"


def test_add_item_to_record_exception(fpm, monkeypatch):
    # Simulate an exception in device_specific_processing.
    def raise_exception(src_path, record_path, file_id, extension):
        raise Exception("Test error")
    fpm.file_processor.device_specific_processing = raise_exception

    move_exception_called = False
    def fake_move_to_exception_folder(src, prefix, ext):
        nonlocal move_exception_called
        move_exception_called = True
    monkeypatch.setattr(
        "src.processing.file_process_manager.StorageManager.move_to_exception_folder",
        fake_move_to_exception_folder
    )

    test_path = "/fake/path/ABC-DEF-sample.txt"
    prefix = "ABC-DEF-sample"
    fpm.add_item_to_record(None, test_path, prefix, ".txt")
    # Verify that an error was shown.
    assert len(fpm.ui.calls["show_error"]) > 0
    # Verify that the exception folder move was triggered.
    assert move_exception_called

def test_sync_records_and_logs(fpm):
    # Set initial flags.
    fpm.records.synced = False
    fpm.records.logs_synced = False
    fpm.sync_records_to_database()
    fpm.sync_logs_to_database()
    # Verify that the dummy record manager flags have been set.
    assert fpm.records.synced is True
    assert fpm.records.logs_synced is True
