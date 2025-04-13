from pathlib import Path
import tkinter as tk
import pytest
from unittest.mock import MagicMock
from core.processing.file_process_manager import FileProcessManager, FileProcessorBase
from core.processing.filename_validator import FilenameValidator
from core.records.local_record import LocalRecord
from core.records.id_generator import IdGenerator


# --- Fixture to disable real I/O operations ---


@pytest.fixture(autouse=True)
def prevent_filesystem_writes(monkeypatch):
    # Block filesystem modifications
    monkeypatch.setattr("pathlib.Path.mkdir", lambda *args, **kwargs: None)
    monkeypatch.setattr("os.rename", lambda *args, **kwargs: None)
    monkeypatch.setattr("shutil.move", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "src.records.record_persistence.save_persisted_records", lambda x: None
    )


# --- Dummy classes to simulate dependencies ---


class DummyFileProcessor(FileProcessorBase):
    def __init__(self, valid_datatype=True, appendable=True):
        self.valid_datatype = valid_datatype
        self.appendable = appendable

    def device_specific_preprocessing(self, src_path: str) -> str:
        return src_path

    def is_valid_datatype(self, path: str) -> bool:
        return self.valid_datatype

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
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
            "prompt_append_record": [],
            "show_rename_dialog": [],
        }
        self.prompt_rename_return = None
        self.prompt_append_record_return = None
        self.show_rename_dialog_return = None  # NEW

    def show_warning(self, title, message):
        self.calls["show_warning"].append((title, message))

    def show_info(self, title, message):
        self.calls["show_info"].append((title, message))

    def show_error(self, title, message):
        self.calls["show_error"].append((title, message))

    def prompt_rename(self):
        self.calls["prompt_rename"].append("called")
        return self.prompt_rename_return

    def show_rename_dialog(self, attempted, analysis):  # NEW
        self.calls["show_rename_dialog"].append((attempted, analysis))
        return self.show_rename_dialog_return

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
        file_processor=file_processor,
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

    monkeypatch.setattr(
        "src.processing.file_process_manager.RecordManager",
        lambda sync_manager: DummyRecordManagerWithPending(),
    )

    fpm = FileProcessManager(
        ui=ui,
        sync_manager=sync_manager,
        session_manager=session_manager,
        file_processor=file_processor,
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
        fake_move_to_exception_folder,
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
        lambda prefix: "dummy_record_path",
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

    fpm._handle_append_to_synced_record(
        record, "/fake/path/ABC-DEF-sample.txt", prefix, ".txt"
    )
    # Verify that prompt_append_record was called with the correct prefix.
    assert fpm.ui.calls["prompt_append_record"][0] == prefix
    # Verify that add_item_to_record was called.
    assert add_item_called


def test_append_to_synced_record_decline(fpm, monkeypatch):
    # Setup: Create a synced record that already has all files uploaded
    prefix = "ABC-DEF-sample"
    record_id = IdGenerator.generate_record_id(prefix)
    record = LocalRecord(identifier=record_id)
    record.is_in_db = True
    record.files_uploaded = {"/fake/path/file": True}
    fpm.records.records[record_id] = record

    # Make the file processor allow appending (so we reach the prompt)
    fpm.file_processor.appendable = True

    # Simulate user declining the append prompt
    fpm.ui.prompt_append_record_return = False

    # Track that rename loop is triggered
    rename_loop_called = False

    # Simulate the user entering a valid new name during rename dialog
    def fake_rename_loop(filename_prefix, *args, **kwargs):
        nonlocal rename_loop_called
        rename_loop_called = True
        return "abc-def-sample-renamed"  # New valid name

    monkeypatch.setattr(fpm, "_interactive_rename_loop", fake_rename_loop)

    # Track that _route_item is triggered with the renamed prefix
    routed_prefix = None

    def fake_route_item(src_path, filename_prefix, extension):
        nonlocal routed_prefix
        routed_prefix = filename_prefix

    monkeypatch.setattr(fpm, "_route_item", fake_route_item)

    # --- Act ---
    fpm._handle_append_to_synced_record(
        record, "/fake/path/ABC-DEF-sample.txt", prefix, ".txt"
    )

    # --- Assert ---
    assert (
        rename_loop_called
    ), "Rename loop should be triggered after user declines append"
    assert (
        routed_prefix == "abc-def-sample-renamed"
    ), "Route item should be called with new prefix"


def test_append_to_unsynced_record_no_prompt(fpm):
    # Create an existing record that is NOT in DB
    prefix = "user-inst-sample"
    record_id = IdGenerator.generate_record_id(prefix.lower())
    record = LocalRecord(identifier=record_id)
    record.is_in_db = False  # Not in DB => unsynced
    fpm.records.records[record_id] = record

    fpm.ui.prompt_append_record_return = None  # Should never be called
    fpm.file_processor.appendable = True

    fpm._route_item("/fake/path/user-inst-sample.txt", prefix, ".txt")

    # If the record is not in DB, we should NOT see prompt_append_record
    assert len(fpm.ui.calls["prompt_append_record"]) == 0
    # A new file item should be appended
    assert len(record.files_uploaded) == 1


def test_handle_unappendable_record_flow(fpm, monkeypatch):
    # Force is_appendable=False
    fpm.file_processor.appendable = False

    prefix = "XYZ-TEST-sample01"
    record_id = IdGenerator.generate_record_id(prefix.lower())
    rec = LocalRecord(identifier=record_id)
    fpm.records.records[record_id] = rec

    handle_unappendable_called = False

    def fake_handle_unappendable(src_path, fn_prefix, ext):
        nonlocal handle_unappendable_called
        handle_unappendable_called = True

    monkeypatch.setattr(fpm, "_handle_unappendable_record", fake_handle_unappendable)

    # Route the file with the same prefix
    fpm._route_item("/fake/path/XYZ-TEST-sample01.txt", prefix, ".txt")

    assert (
        handle_unappendable_called
    ), "Should invoke _handle_unappendable_record for unappendable scenario"


def test_auto_rename_when_conflict(fpm, monkeypatch):
    """
    If there's a conflict, ensure the manager calls 'get_unique_filename'
    and completes the file addition. This is more about PathManager, but
    we can still check the flow in FileProcessManager.
    """
    # Make the record exist
    prefix = "user-inst-sample"
    record_id = IdGenerator.generate_record_id(prefix)
    rec = LocalRecord(identifier=record_id)
    fpm.records.records[record_id] = rec

    # Suppose the device processor calls the PathManager to get a unique filename
    def mock_device_specific_processing(src_path, record_path, file_id, extension):
        # This is typically where you'd call PathManager.get_unique_filename
        # We'll mimic that there's a conflict, so you get "fileid_02.txt" eventually
        return f"{record_path}/fileid_02{extension}", "dummy_datatype"

    fpm.file_processor.device_specific_processing = mock_device_specific_processing

    # We'll patch out the record path
    monkeypatch.setattr(
        "src.processing.file_process_manager.PathManager.get_record_path",
        lambda pfx: "dummy_record_path",
    )

    # Act
    fpm.add_item_to_record(rec, "/fake/path/user-inst-sample.txt", prefix, ".txt")

    # The record should now contain the final path with 'fileid_02'
    uploaded_paths = list(rec.files_uploaded.keys())
    assert len(uploaded_paths) == 1
    assert "fileid_02.txt" in uploaded_paths[0]


def test_invalid_filename_triggers_prompt(fpm, monkeypatch):
    test_path = "/fake/path/invalid--name.txt"

    # Force sanitize_and_validate to return is_valid_format = False
    monkeypatch.setattr(
        "src.processing.file_process_manager.FilenameValidator.sanitize_and_validate",
        lambda prefix: ("sanitized-invalid--name", False),
    )

    # Mock prompt rename to simulate user cancel
    fpm.ui.prompt_rename_return = {
        "name": "ABC",
        "institute": "DEF",
        "sample_ID": "sample",
    }

    rename_called = False

    def fake_prompt_item_rename(src_path, prefix, ext, **kwargs):
        nonlocal rename_called
        rename_called = True

    monkeypatch.setattr(fpm, "_rename_flow_controller", fake_prompt_item_rename)

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
        fake_move_to_rename_folder,
    )

    fpm._rename_flow_controller(test_path, prefix, extension)

    assert move_called
    assert fpm.ui.calls["show_info"][-1][0] == "Operation Cancelled"


def test_get_valid_rename_loops_until_valid(monkeypatch, fpm):
    call_order = []

    def fake_explain_violation(name):
        return {"valid": False, "reasons": ["bad"], "highlight_spans": [(0, 1)]}

    def fake_analyze_user_input(data):
        call_order.append("analyze")
        if data["name"] == "Valid":
            return {
                "valid": True,
                "sanitized": "valid-institute-sample",
                "reasons": [],
                "highlight_spans": [],
            }
        return {"valid": False, "reasons": ["still bad"], "highlight_spans": [(0, 1)]}

    def fake_show_rename_dialog(name, analysis):
        call_order.append("show_dialog")
        return {"name": "Valid", "institute": "Institute", "sample_ID": "Sample"}

    monkeypatch.setattr(
        "src.processing.file_process_manager.FilenameValidator.explain_filename_violation",
        fake_explain_violation,
    )
    monkeypatch.setattr(
        "src.processing.file_process_manager.FilenameValidator.analyze_user_input",
        fake_analyze_user_input,
    )
    monkeypatch.setattr(fpm.ui, "show_rename_dialog", fake_show_rename_dialog)

    result = fpm._interactive_rename_loop(
        "bad--name",
    )
    assert result == "valid-institute-sample"
    assert call_order.count("analyze") == 1
    assert call_order.count("show_dialog") == 1


def test_process_item_elid_directory(fpm, monkeypatch):
    """
    Simulate that the device-specific processor sees a directory with .elid,
    ensuring the manager calls device_specific_processing and updates the record.
    """

    # Make the file processor treat directories as valid if they contain .elid
    def mock_is_valid_datatype(path):
        # We'll pretend everything that ends with "folder" is a valid .elid directory
        return path.endswith("elid_folder")

    fpm.file_processor.is_valid_datatype = mock_is_valid_datatype

    # We'll patch device_specific_processing to see if it's called with the folder path
    def mock_device_processing(src_path, record_path, file_id, extension):
        # Normally you'd flatten directories, rename, etc.
        # For test, just return a final path
        return f"{record_path}/processed_elid_dir", "elid"

    fpm.file_processor.device_specific_processing = mock_device_processing

    # Patch path manager for record path
    monkeypatch.setattr(
        "src.processing.file_process_manager.PathManager.get_record_path",
        lambda prefix: "dummy_record_elid_path",
    )

    test_path = "/fake/path/sample-elid_folder"  # directory name
    fpm.process_item(test_path)

    # A new record is created with the sanitized prefix
    expected_record_id = IdGenerator.generate_record_id("sample-elid_folder".lower())
    assert (
        expected_record_id in fpm.records.records
    ), "Record should be created for ELID directory"

    record = fpm.records.records[expected_record_id]
    # The device_specific_processing returned "dummy_record_elid_path/processed_elid_dir"
    # So we expect that path in the record
    assert any("processed_elid_dir" in k for k in record.files_uploaded.keys())
    # Confirm the record's datatype is 'elid'
    assert record.datatype == "elid"


def test_add_item_to_record_success_path(fpm, monkeypatch):
    # Setup
    fpm.session_manager.session_active = False
    record = None
    test_path = "/fake/path/ABC-DEF-sample.txt"
    filename_prefix = "abc-def-sample"
    extension = ".txt"

    monkeypatch.setattr(
        "src.processing.file_process_manager.PathManager.get_record_path",
        lambda prefix: "record_path",
    )
    monkeypatch.setattr(
        "src.processing.file_process_manager.IdGenerator.generate_file_id",
        lambda prefix: "fileid",
    )

    final_result = {"moved": False}

    def fake_device_specific_processing(src, rec_path, file_id, ext):
        final_result["moved"] = True
        return f"{rec_path}/fileid{ext}", "test_type"

    fpm.file_processor.device_specific_processing = fake_device_specific_processing

    fpm.add_item_to_record(record, test_path, filename_prefix, extension)
    # Should trigger UI info and session start
    assert final_result["moved"] is True
    assert fpm.session_manager.start_session_called
    assert ("Success", "File renamed to 'fileid.txt'") in fpm.ui.calls["show_info"]


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
        fake_move_to_exception_folder,
    )

    test_path = "/fake/path/ABC-DEF-sample.txt"
    prefix = "ABC-DEF-sample"
    fpm.add_item_to_record(None, test_path, prefix, ".txt")
    # Verify that an error was shown.
    assert len(fpm.ui.calls["show_error"]) > 0
    # Verify that the exception folder move was triggered.
    assert move_exception_called


def test_route_item_exception_path(fpm, monkeypatch):
    # Force an exception in the route logic
    def raise_exception(*args, **kwargs):
        raise RuntimeError("Boom!")

    monkeypatch.setattr(
        "src.processing.file_process_manager.FilenameValidator.sanitize_and_validate",
        raise_exception,
    )

    move_exc_called = False

    def fake_move_to_exception_folder(src, prefix, extension):
        nonlocal move_exc_called
        move_exc_called = True

    monkeypatch.setattr(
        "src.processing.file_process_manager.StorageManager.move_to_exception_folder",
        fake_move_to_exception_folder,
    )

    fpm.process_item("/fake/path/explosive.txt")
    # The UI should show an error
    assert len(fpm.ui.calls["show_error"]) >= 1
    # The file should go to exception folder
    assert move_exc_called


def test_process_item_resets_session_if_active(fpm):
    # Make the session already active
    fpm.session_manager.session_active = True
    fpm.session_manager.reset_timer_called = False

    # Process a valid file
    test_path = "/fake/path/ABC-DEF-sample.txt"
    fpm.process_item(test_path)

    # We expect reset_timer to be called instead of start_session
    assert (
        fpm.session_manager.reset_timer_called
    ), "SessionManager should reset timer if session is active"
    assert (
        not fpm.session_manager.start_session_called
    ), "Should not start a new session"


def test_sync_records_and_logs(fpm):
    # Set initial flags.
    fpm.records.synced = False
    fpm.records.logs_synced = False
    fpm.sync_records_to_database()
    fpm.sync_logs_to_database()
    # Verify that the dummy record manager flags have been set.
    assert fpm.records.synced is True
    assert fpm.records.logs_synced is True


def test_process_item_elid_directory(fpm, monkeypatch):
    """
    Simulate that the device-specific processor sees a directory with .elid,
    ensuring the manager calls device_specific_processing and updates the record.
    """

    # Make the file processor treat directories as valid if they contain .elid
    def mock_is_valid_datatype(path):
        # We'll pretend everything that ends with "folder" is a valid .elid directory
        return path.endswith("elid_folder")

    fpm.file_processor.is_valid_datatype = mock_is_valid_datatype

    # We'll patch device_specific_processing to see if it's called with the folder path
    def mock_device_processing(src_path, record_path, file_id, extension):
        # Normally you'd flatten directories, rename, etc.
        # For test, just return a final path
        return f"{record_path}/processed_elid_dir", "elid"

    fpm.file_processor.device_specific_processing = mock_device_processing

    # Patch path manager for record path
    monkeypatch.setattr(
        "src.processing.file_process_manager.PathManager.get_record_path",
        lambda prefix: "dummy_record_elid_path",
    )

    test_path = "/fake/path/usr-inst-elid_folder"  # directory name
    fpm.process_item(test_path)

    # A new record is created with the sanitized prefix
    expected_record_id = IdGenerator.generate_record_id("usr-inst-elid_folder".lower())
    assert (
        expected_record_id in fpm.records.records
    ), "Record should be created for ELID directory"

    record = fpm.records.records[expected_record_id]
    # The device_specific_processing returned "dummy_record_elid_path/processed_elid_dir"
    # So we expect that path in the record
    assert any("processed_elid_dir" in k for k in record.files_uploaded.keys())
    # Confirm the record's datatype is 'elid'
    assert record.datatype == "elid"
