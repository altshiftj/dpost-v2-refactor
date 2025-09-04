from pathlib import Path
import tkinter as tk
import pytest
from unittest.mock import MagicMock

from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import generate_record_id

from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager
from ipat_watchdog.core.config.settings_base import BaseSettings
from ipat_watchdog.core.config.device_settings_base import DeviceSettings
from ipat_watchdog.core.config.global_settings import PCSettings

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
        DEVICE_TYPE = 'TEST'
        DEVICE_RECORD_KADI_ID = 'test_01'  # Add this required attribute
        FILENAME_PATTERN = BaseSettings.FILENAME_PATTERN
        ALLOWED_EXTENSIONS = {'.txt', '.tif'}
        DEBOUNCE_TIME = 0
        SESSION_TIMEOUT = 1
        
        @classmethod
        def get_device_id(cls) -> str:
            return "test_device"
            
        def matches_file(self, filepath: str) -> bool:
            return Path(filepath).suffix.lower() in {'.txt', '.tif'}
    
    # Set up settings manager with global and device settings
    global_settings = PCSettings()
    device_settings = TestDeviceSettings()
    settings_manager = SettingsManager(global_settings, [device_settings])
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

    def all_records_uploaded(self):
        return all(record.all_files_uploaded() for record in self.records.values())

    def get_record_by_id(self, record_id):
        return self.records.get(record_id)

    def create_record(self, filename_prefix):
        record_id = generate_record_id(filename_prefix)
        new_record = LocalRecord(identifier=record_id)
        self.records[record_id] = new_record
        return new_record

    def add_item_to_record(self, path, record):
        record.files_uploaded[path] = True

    def sync_records_to_database(self):
        self.synced = True

# --- Fixture for FileProcessManager instance ---
@pytest.fixture
def fpm():
    ui = HeadlessUI()
    session_manager = FakeSessionManager()
    sync_manager = DummySyncManager(ui=ui)
    # For test simplicity, we'll pass a file processor for backward compatibility
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

        def all_records_uploaded(self):
            return False

        def sync_records_to_database(self):
            self.synced = True

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
    assert fpm_inst.records.synced is True


def test_process_item_invalid_datatype(fpm, monkeypatch):
    fpm.file_processor.valid_datatype = False
    test_path = "/fake/path/invalid.txt"

    move_exception_called = False
    def fake_move_to_exception_folder(src, prefix, ext):
        nonlocal move_exception_called
        move_exception_called = True

    import ipat_watchdog.core.processing.file_process_manager as mod
    monkeypatch.setattr(mod, "move_to_exception_folder", fake_move_to_exception_folder)

    fpm.process_item(test_path)
    assert len(fpm.ui.calls["show_warning"]) > 0
    assert move_exception_called
    assert len(fpm.records.records) == 0


def test_process_item_valid_new_record(fpm, monkeypatch):
    fpm.file_processor.valid_datatype = True
    test_path = "/fake/path/ABC-DEF-sample.txt"

    import ipat_watchdog.core.processing.file_process_manager as mod
    monkeypatch.setattr(mod, "get_record_path", lambda prefix: "dummy_record_path")

    expected_id = generate_record_id("abc-def-sample")
    fpm.process_item(test_path)
    assert expected_id in fpm.records.records
    assert fpm.session_manager.start_session_called


def test_append_to_synced_record_confirm(fpm, monkeypatch):
    prefix = "ABC-DEF-sample"
    rec_id = generate_record_id(prefix.lower())
    record = LocalRecord(identifier=rec_id)
    record.is_in_db = True
    record.files_uploaded = {"/fake/path/file": True}
    fpm.records.records[rec_id] = record

    fpm.file_processor.appendable = True
    fpm.ui.prompt_append_record_return = True

    add_called = False
    orig_add = fpm.add_item_to_record
    def fake_add_item(record_arg, src_path, filename_prefix, extension, notify=True):
        nonlocal add_called
        add_called = True
        orig_add(record_arg, src_path, filename_prefix, extension, notify)

    monkeypatch.setattr(fpm, "add_item_to_record", fake_add_item)

    fpm._handle_append_to_synced_record(
        record, "/fake/path/ABC-DEF-sample.txt", prefix, ".txt", fpm.file_processor
    )
    assert fpm.ui.calls["prompt_append_record"][0] == prefix
    assert add_called


def test_append_to_synced_record_decline(fpm, monkeypatch):
    prefix = "ABC-DEF-sample"
    rec_id = generate_record_id(prefix)
    record = LocalRecord(identifier=rec_id)
    record.is_in_db = True
    record.files_uploaded = {"/fake/path/file": True}
    fpm.records.records[rec_id] = record

    fpm.file_processor.appendable = True
    fpm.ui.prompt_append_record_return = False

    rename_loop_called = False
    def fake_loop(filename_prefix, *args, **kwargs):
        nonlocal rename_loop_called
        rename_loop_called = True
        return "abc-def-sample-renamed"

    monkeypatch.setattr(fpm, "_interactive_rename_loop", fake_loop)

    routed = None
    def fake_route(src, pfx, ext, file_processor):
        nonlocal routed
        routed = pfx

    monkeypatch.setattr(fpm, "_route_item", fake_route)

    fpm._handle_append_to_synced_record(
        record, "/fake/path/ABC-DEF-sample.txt", prefix, ".txt", fpm.file_processor
    )
    assert rename_loop_called
    assert routed == "abc-def-sample-renamed"


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


def test_handle_unappendable_record_flow(fpm, monkeypatch):
    fpm.file_processor.appendable = False

    prefix = "XYZ-TEST-sample01"
    rec_id = generate_record_id(prefix.lower())
    rec = LocalRecord(identifier=rec_id)
    fpm.records.records[rec_id] = rec

    handle_called = False
    def fake_handle_unappendable(src_path, fn_prefix, ext):
        nonlocal handle_called
        handle_called = True

    monkeypatch.setattr(fpm, "_handle_unappendable_record", fake_handle_unappendable)

    fpm._route_item("/fake/path/XYZ-TEST-sample01.txt", prefix, ".txt", fpm.file_processor)
    assert handle_called


def test_auto_rename_when_conflict(fpm, monkeypatch):
    prefix = "user-inst-sample"
    rec_id = generate_record_id(prefix)
    rec = LocalRecord(identifier=rec_id)
    fpm.records.records[rec_id] = rec

    def mock_device_specific_processing(src_path, record_path, file_id, extension):
        return f"{record_path}/fileid_02{extension}", "dummy_datatype"
    fpm.file_processor.device_specific_processing = mock_device_specific_processing

    import ipat_watchdog.core.processing.file_process_manager as mod
    monkeypatch.setattr(mod, "get_record_path", lambda pfx: "dummy_record_path")

    fpm.add_item_to_record(rec, "/fake/path/user-inst-sample.txt", prefix, ".txt")
    uploaded_paths = list(rec.files_uploaded.keys())
    assert len(uploaded_paths) == 1
    assert "fileid_02.txt" in uploaded_paths[0]


def test_invalid_filename_triggers_prompt(fpm, monkeypatch):
    test_path = "/fake/path/invalid--name.txt"

    import ipat_watchdog.core.processing.file_process_manager as mod
    monkeypatch.setattr(mod, "sanitize_and_validate", lambda prefix: ("sanitized-invalid--name", False))

    fpm.ui.prompt_rename_return = {"name": "ABC", "institute": "DEF", "sample_ID": "sample"}

    rename_called = False
    def fake_rename(src_path, prefix, ext, **kwargs):
        nonlocal rename_called
        rename_called = True

    monkeypatch.setattr(fpm, "_rename_flow_controller", fake_rename)

    fpm.process_item(test_path)
    assert rename_called


def test_rename_cancellation_moves_file(fpm, monkeypatch):
    test_path = "/fake/path/ABC-DEF-cancel.txt"
    prefix = "ABC-DEF-cancel"
    extension = ".txt"

    fpm.ui.prompt_rename_return = None

    move_called = False
    def fake_move_to_rename_folder(src, pfx, ext):
        nonlocal move_called
        move_called = True

    import ipat_watchdog.core.processing.file_process_manager as mod
    monkeypatch.setattr(mod, "move_to_rename_folder", fake_move_to_rename_folder)

    fpm._rename_flow_controller(test_path, prefix, extension)
    assert move_called
    assert fpm.ui.calls["show_info"][ -1][0] == "Operation Cancelled"


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

    import ipat_watchdog.core.processing.file_process_manager as mod
    monkeypatch.setattr(mod, "explain_filename_violation", fake_explain_violation)
    monkeypatch.setattr(mod, "analyze_user_input", fake_analyze_user_input)
    fpm.ui.show_rename_dialog = fake_show_rename_dialog

    result = fpm._interactive_rename_loop("bad--name")
    assert result == "valid-institute-sample"
    assert call_order.count("analyze") == 1
    assert call_order.count("show_dialog") == 1


def test_process_item_elid_directory(fpm, monkeypatch):
    def mock_is_valid_datatype(path):
        return path.endswith("elid_folder")
    fpm.file_processor.is_valid_datatype = mock_is_valid_datatype

    def mock_device_processing(src_path, record_path, file_id, extension):
        return f"{record_path}/processed_elid_dir", "elid"
    fpm.file_processor.device_specific_processing = mock_device_processing

    import ipat_watchdog.core.processing.file_process_manager as mod
    monkeypatch.setattr(mod, "get_record_path", lambda prefix: "dummy_record_elid_path")

    test_path = "/fake/path/usr-inst-elid_folder"
    fpm.process_item(test_path)

    # Ensure device context is set for generate_record_id call
    from ipat_watchdog.core.config.settings_store import SettingsStore
    settings_manager = SettingsStore.get_manager()
    # Find the test device settings and set it as current
    for device in settings_manager._devices.values():
        if device.get_device_id() == "test_device":
            settings_manager.set_current_device(device)
            break

    expected_id = generate_record_id("usr-inst-elid_folder")
    assert expected_id in fpm.records.records
    record = fpm.records.records[expected_id]
    assert any("processed_elid_dir" in k for k in record.files_uploaded.keys())
    assert record.datatype == "elid"


def test_add_item_to_record_success_path(fpm, monkeypatch):
    fpm.session_manager.session_active = False
    record = None
    test_path = "/fake/path/ABC-DEF-sample.txt"
    filename_prefix = "abc-def-sample"
    extension = ".txt"

    import ipat_watchdog.core.processing.file_process_manager as mod
    monkeypatch.setattr(mod, "get_record_path", lambda prefix: "record_path")
    monkeypatch.setattr(mod, "generate_file_id", lambda prefix: "fileid")

    final_result = {"moved": False}
    def fake_device_specific_processing(src, rec, fid, ext):
        final_result["moved"] = True
        return f"{rec}/fileid{ext}", "test_type"

    fpm.file_processor.device_specific_processing = fake_device_specific_processing
    fpm.add_item_to_record(record, test_path, filename_prefix, extension)
    assert final_result["moved"]
    assert fpm.session_manager.start_session_called
    assert ("Success", "File renamed to 'fileid.txt'") in fpm.ui.calls["show_info"]


def test_add_item_to_record_exception(fpm, monkeypatch):
    def raise_exc(src, rec_path, fid, ext):
        raise Exception("Test error")
    fpm.file_processor.device_specific_processing = raise_exc

    move_called = False
    def fake_move_to_exception_folder(src, prefix, ext):
        nonlocal move_called
        move_called = True

    import ipat_watchdog.core.processing.file_process_manager as mod
    monkeypatch.setattr(mod, "move_to_exception_folder", fake_move_to_exception_folder)

    fpm.add_item_to_record(None, "/fake/path/ABC-DEF-sample.txt", "ABC-DEF-sample", ".txt")
    assert len(fpm.ui.calls["show_error"]) > 0
    assert move_called


def test_route_item_exception_path(fpm, monkeypatch):
    import ipat_watchdog.core.processing.file_process_manager as mod
    monkeypatch.setattr(mod, "sanitize_and_validate", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Boom!")))

    exc_called = False
    def fake_move(src, prefix, extension):
        nonlocal exc_called
        exc_called = True
    monkeypatch.setattr(mod, "move_to_exception_folder", fake_move)

    fpm.process_item("/fake/path/explosive.txt")
    assert len(fpm.ui.calls["show_error"]) >= 1
    assert exc_called


def test_process_item_resets_session_if_active(fpm):
    fpm.session_manager.session_active = True
    fpm.session_manager.reset_timer_called = False

    fpm.process_item("/fake/path/ABC-DEF-sample.txt")
    assert fpm.session_manager.reset_timer_called
    assert not fpm.session_manager.start_session_called


def test_sync_records(fpm):
    fpm.records.synced = False
    fpm.sync_records_to_database()
    assert fpm.records.synced is True
