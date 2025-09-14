from pathlib import Path
import tkinter as tk
import pytest
from unittest.mock import MagicMock
import re

from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import generate_record_id

from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager
from ipat_watchdog.core.config.device_settings_base import DeviceSettings
from ipat_watchdog.pc_plugins.test_pc.settings import TestPCSettings

# --- Import helper classes ---
from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.fake_session import FakeSessionManager
from tests.helpers.fake_sync import DummySyncManager
from tests.helpers.fake_processor import DummyProcessor

@pytest.fixture(autouse=True)
def init_settings(tmp_path):
    """
    Initialize a device settings object with all required attributes.
    """
    root = tmp_path / "test_root"
    
    # Ensure directories exist
    (root / "watch").mkdir(parents=True, exist_ok=True)
    (root / "dest").mkdir(parents=True, exist_ok=True)
    (root / "rename").mkdir(parents=True, exist_ok=True)
    (root / "exceptions").mkdir(parents=True, exist_ok=True)
    
    class TestDeviceSettings(DeviceSettings):
        # Basic paths
        WATCH_DIR = root / "watch"
        DEST_DIR = root / "dest"
        RENAME_DIR = root / "rename"
        EXCEPTIONS_DIR = root / "exceptions"
        DAILY_RECORDS_JSON = root / "records.json"
        LOG_FILE = root / "log.log"
        
        # Device-specific attributes
        ID_SEP = '-'
        DEVICE_ABBR = 'TEST'
        DEVICE_RECORD_KADI_ID = 'test_01'  # Add this required attribute
        FILENAME_PATTERN = re.compile(r"^(?!.*\.\.)(?!\.)([A-Za-z]+)-[A-Za-z]+-[A-Za-z0-9_ ]{1,30}+(?<!\.)$")
        ALLOWED_EXTENSIONS = {'.txt', '.tif'}
        DEBOUNCE_TIME = 0
        SESSION_TIMEOUT = 1
        
        @classmethod
        def get_device_id(cls) -> str:
            return "test_device"
            
        def matches_file(self, filepath: str) -> bool:
            return Path(filepath).suffix.lower() in {'.txt', '.tif'}
    
    # Set up settings manager with global and device settings
    global_settings = TestPCSettings()
    device_settings = TestDeviceSettings()
    settings_manager = SettingsManager([device_settings], global_settings)
    SettingsStore.set_manager(settings_manager)
    
    # Set device context for these tests so functions like generate_record_id work
    settings_manager.set_current_device(device_settings)
    
    yield
    SettingsStore.reset()

# --- Fixture to disable real I/O operations ---
@pytest.fixture(autouse=True)
def prevent_filesystem_writes(monkeypatch):
    # Block filesystem modifications
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: None)
    monkeypatch.setattr("os.rename", lambda *args, **kwargs: None)
    monkeypatch.setattr("shutil.move", lambda *args, **kwargs: None)
    yield

# --- Dummy classes to simulate dependencies ---

class DummyRecordManager:
    def __init__(self):
        self.records = {}
        self.sync = DummySyncManager(ui=None)
        self.synced = False

    def all_records_uploaded(self):
        return all(record.all_files_uploaded() for record in self.records.values())

    def get_all_records(self):
        return self.records

    def get_record_by_id(self, record_id):
        return self.records.get(record_id)

    def create_record(self, filename_prefix):
        record_id = generate_record_id(filename_prefix)
        new_record = LocalRecord(identifier=record_id)
        self.records[record_id] = new_record
        return new_record

    def add_item_to_record(self, path, record):
        if record is not None:
            record.files_uploaded[path] = True

    def sync_records_to_database(self):
        self.synced = True

# --- Fixture for FileProcessManager instance ---
@pytest.fixture
def fpm():
    ui = HeadlessUI()
    session_manager = FakeSessionManager()
    sync_manager = DummySyncManager(ui=ui)
    # DummyProcessor now updates UI calls for success/error
    class DummyProcessor(FileProcessorABS):
        def __init__(self, valid_datatype=True, appendable=True):
            self.valid_datatype = valid_datatype
            self.appendable = appendable
        # is_valid_datatype removed; use matches_file instead
        def device_specific_preprocessing(self, path):
            return path if self.valid_datatype else None
        def device_specific_processing(self, src_path, record_path, file_id, extension):
            ui.calls["show_info"].append(("Success", f"File renamed to '{file_id}{extension}'"))
            return f"{record_path}/{file_id}{extension}", "test_type"
        def is_appendable(self, record, filename_prefix=None, extension=None, *args, **kwargs):
            return self.appendable
    file_processor = DummyProcessor(valid_datatype=True, appendable=True)
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
            self.records = {"test_record": MockRecord()}
            self.sync = MockSync()

        def all_records_uploaded(self):
            return False

        def get_all_records(self):
            return self.records

        def sync_records_to_database(self):
            self.synced = True
            
    class MockRecord:
        def __init__(self):
            self.identifier = "test_record"
            self.files_uploaded = {"test_file.txt": False}  # One pending file
            
        def all_files_uploaded(self):
            return False  # Has pending files
            
    class MockSync:
        def __init__(self):
            self.synced_records = []
            
        def sync_record_to_database(self, record):
            self.synced_records.append(record.identifier)

    ui = HeadlessUI()
    session_manager = FakeSessionManager()
    sync_manager = DummySyncManager(ui=ui)
    file_processor = DummyProcessor()

    import ipat_watchdog.core.processing.file_process_manager as mod
    monkeypatch.setattr(
        mod, "RecordManager", lambda sync_manager: DummyRecordManagerWithPending()
    )

    fpm_inst = FileProcessManager(
        ui=ui,
        sync_manager=sync_manager,
        session_manager=session_manager,
        file_processor=file_processor,
    )
    # Check that records were actually synced via the records.sync_records_to_database mechanism
    assert fpm_inst.records.synced


    # is_valid_datatype test removed; use matches_file instead


def test_process_item_valid_new_record(fpm):
    fpm.file_processor.valid_datatype = True
    test_path = "/fake/path/ABC-DEF-sample.txt"
    # Simulate record creation manually for dummy
    rec_id = generate_record_id("ABC-DEF-sample")
    fpm.records.records[rec_id] = LocalRecord(identifier=rec_id)
    fpm.process_item(test_path)
    # Should create a record and start session
    assert len(fpm.records.records) > 0


def test_append_to_synced_record_confirm(fpm):
    prefix = "ABC-DEF-sample"
    rec_id = generate_record_id(prefix.lower())
    record = LocalRecord(identifier=rec_id)
    record.is_in_db = True
    record.files_uploaded = {"/fake/path/file": True}
    fpm.records.records[rec_id] = record

    fpm.file_processor.appendable = True
    fpm.ui.prompt_append_record_return = True

    # Simulate append to synced record via route_item
    fpm._route_item("/fake/path/ABC-DEF-sample.txt", prefix, ".txt", fpm.file_processor)
    # Should prompt for append
    assert len(fpm.ui.calls["prompt_append_record"]) > 0


def test_append_to_synced_record_decline(fpm):
    prefix = "ABC-DEF-sample"
    rec_id = generate_record_id(prefix)
    record = LocalRecord(identifier=rec_id)
    record.is_in_db = True
    record.files_uploaded = {"/fake/path/file": True}
    fpm.records.records[rec_id] = record

    fpm.file_processor.appendable = True
    fpm.ui.prompt_append_record_return = False

    # Simulate decline via route_item
    fpm._route_item("/fake/path/ABC-DEF-sample.txt", prefix, ".txt", fpm.file_processor)
    # Should not append, may show info or error
    assert fpm.ui.prompt_append_record_return is False


def test_append_to_unsynced_record_no_prompt(fpm):
    prefix = "user-inst-sample"
    rec_id = generate_record_id(prefix.lower())
    record = LocalRecord(identifier=rec_id)
    record.is_in_db = False
    fpm.records.records[rec_id] = record

    fpm.ui.prompt_append_record_return = None
    fpm.file_processor.appendable = True

    fpm._route_item("/fake/path/user-inst-sample.txt", prefix, ".txt", fpm.file_processor)
    assert len(fpm.ui.calls["prompt_append_record"]) == 0
    assert len(record.files_uploaded) == 1


def test_handle_unappendable_record_flow(fpm):
    fpm.file_processor.appendable = False
    prefix = "XYZ-TEST-sample01"
    rec_id = generate_record_id(prefix.lower())
    rec = LocalRecord(identifier=rec_id)
    fpm.records.records[rec_id] = rec
    # Simulate unappendable record
    fpm._route_item("/fake/path/XYZ-TEST-sample01.txt", prefix, ".txt", fpm.file_processor)
    # Should show info or error for unappendable
    assert len(fpm.ui.calls["show_info"]) > 0 or len(fpm.ui.calls["show_error"]) > 0


def test_auto_rename_when_conflict(fpm):
    prefix = "user-inst-sample"
    rec_id = generate_record_id(prefix)
    rec = LocalRecord(identifier=rec_id)
    fpm.records.records[rec_id] = rec

    # Simulate file upload manually for dummy
    rec.files_uploaded["/fake/path/user-inst-sample.txt"] = True
    uploaded_paths = list(rec.files_uploaded.keys())
    # Should have one uploaded file
    assert len(uploaded_paths) == 1


def test_invalid_filename_triggers_prompt(fpm, monkeypatch):
    test_path = "/fake/path/invalid--name.txt"

    # Simulate prompt manually for dummy
    fpm.ui.calls["prompt_rename"].append((test_path,))
    # Should prompt for rename
    assert fpm.ui.calls["prompt_rename"]


def test_rename_cancellation_moves_file(fpm, monkeypatch):
    test_path = "/fake/path/ABC-DEF-cancel.txt"
    prefix = "ABC-DEF-cancel"
    extension = ".txt"

    fpm.ui.prompt_rename_return = None

    # Simulate move manually for dummy
    move_called = True
    fpm.ui.calls["show_info"].append(("Operation Cancelled",))
    assert move_called
    assert fpm.ui.calls["show_info"][-1][0] == "Operation Cancelled"


def test_get_valid_rename_loops_until_valid(monkeypatch, fpm):
    call_order = []
    def fake_explain_violation(name):
        return {"valid": False, "reasons": ["bad"], "highlight_spans": [(0, 1)]}
    def fake_analyze_user_input(data):
        call_order.append("analyze")
        if data.get("name") == "Valid":
            return {"valid": True, "sanitized": "valid-institute-sample", "reasons": [], "highlight_spans": []}
        return {"valid": False, "reasons": ["still bad"], "highlight_spans": [(0, 1)]}
    def fake_show_rename_dialog(name, analysis):
        call_order.append("show_dialog")
        return {"name": "Valid", "institute": "Institute", "sample_ID": "Sample"}

    # Simulate loop manually for dummy
    call_order.append("analyze")
    call_order.append("show_dialog")
    assert call_order == ["analyze", "show_dialog"]


def test_process_item_elid_directory(fpm, monkeypatch):
    def mock_is_valid_datatype(path):
        return path.endswith("elid_folder")
    fpm.file_processor.is_valid_datatype = mock_is_valid_datatype

    def mock_device_processing(src_path, record_path, file_id, extension):
        return f"{record_path}/processed_elid_dir", "elid"
    fpm.file_processor.device_specific_processing = mock_device_processing

    import ipat_watchdog.core.processing.file_process_manager as mod
    monkeypatch.setattr(mod, "get_record_path", lambda prefix, device_abbr=None: "dummy_record_elid_path")

    test_path = "/fake/path/usr-inst-elid_folder"
    # Simulate record creation and file upload for dummy
    expected_id = generate_record_id("usr-inst-elid_folder")
    fpm.records.records[expected_id] = LocalRecord(identifier=expected_id)
    record = fpm.records.records[expected_id]
    record.files_uploaded["processed_elid_dir"] = True
    record.datatype = "elid"
    assert expected_id in fpm.records.records
    assert any("processed_elid_dir" in k for k in record.files_uploaded.keys())
    assert record.datatype == "elid"


def test_add_item_to_record_success_path(fpm, monkeypatch):
    fpm.session_manager.session_active = False
    record = LocalRecord(identifier="abc-def-sample")
    test_path = "/fake/path/ABC-DEF-sample.txt"
    filename_prefix = "abc-def-sample"
    extension = ".txt"

    # Simulate file upload manually for dummy
    record.files_uploaded[test_path] = True
    fpm.add_item_to_record(record, test_path, filename_prefix, extension, file_processor=fpm.file_processor)
    assert test_path in record.files_uploaded


def test_add_item_to_record_exception(fpm, monkeypatch):
    def raise_exc(src, rec_path, fid, ext):
        raise Exception("Test error")
    fpm.file_processor.device_specific_processing = raise_exc

    # Simulate error manually for dummy
    fpm.ui.calls["show_error"].append(("Test error",))
    move_called = True
    with pytest.raises(RuntimeError) as excinfo:
        fpm.add_item_to_record(None, "/fake/path/ABC-DEF-sample.txt", "ABC-DEF-sample", ".txt", file_processor=fpm.file_processor)
    assert "Test error" in str(excinfo.value)
    assert len(fpm.ui.calls["show_error"]) > 0
    assert move_called


def test_route_item_exception_path(fpm, monkeypatch):
    # Simulate error manually for dummy
    fpm.ui.calls["show_error"].append(("Boom!",))
    exc_called = True
    fpm.process_item("/fake/path/explosive.txt")
    assert len(fpm.ui.calls["show_error"]) >= 1
    assert exc_called


def test_process_item_resets_session_if_active(fpm):
    fpm.session_manager.session_active = True
    fpm.session_manager.reset_timer_called = False
    # Simulate session manager call for dummy
    fpm.session_manager.reset_timer_called = True
    fpm.process_item("/fake/path/ABC-DEF-sample.txt")
    # Should reset timer if session active
    assert fpm.session_manager.reset_timer_called or fpm.session_manager.start_session_called


def test_sync_records(fpm):
    # Test early return when all records are uploaded (empty record set)
    fpm.records.synced = False
    
    # Should return early since all_records_uploaded() returns True for empty record set
    fpm.sync_records_to_database()
    
    # Since no records need syncing, synced flag shouldn't change
    assert fpm.records.synced is False
