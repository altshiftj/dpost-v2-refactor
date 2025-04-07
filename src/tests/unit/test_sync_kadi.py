import os
import pytest
from unittest.mock import MagicMock, patch

from src.sync.sync_kadi import KadiSyncManager
from src.records.local_record import LocalRecord
from src.config.settings import (
    DEVICE_ID,
    DEVICE_USER_ID,
    DEVICE_RECORD_ID,
    DEFAULT_REM_RECORD_DESCRIPTION,
    ID_SEP,
    LOG_FILE,
)

# --- Dummy Classes to Simulate KadiManager Resources ---

class DummyKadiUser:
    def __init__(self, user_id="dummy_user"):
        self.id = user_id

class DummyKadiGroup:
    def __init__(self, group_id="dummy_group"):
        self.id = group_id
        self.added_users = []
        self.attributes = {}
    def add_user(self, user_id, role_name):
        self.added_users.append((user_id, role_name))
    def set_attribute(self, key, value):
        self.attributes[key] = value

class DummyKadiRecord:
    def __init__(self):
        self.meta = {"title": "Dummy Device Record"}
        self.uploaded_files = []
        self.tags = []
        self.group_roles = []
        self.users = []
    def set_attribute(self, key, value):
        setattr(self, key, value)
    def add_tag(self, tag):
        self.tags.append(tag)
    def link_record(self, device_record_id, relationship):
        self.link = (device_record_id, relationship)
    def add_group_role(self, group_id, role_name):
        self.group_roles.append((group_id, role_name))
    def add_user(self, user_id, role_name):
        self.users.append((user_id, role_name))
    def upload_file(self, file_path, force=False):
        self.uploaded_files.append((file_path, force))

class DummyKadiManager:
    def __init__(self):
        self.user = MagicMock(return_value=DummyKadiUser("existing_user"))
        self.group = MagicMock()
        self.record = MagicMock(return_value=DummyKadiRecord())

        def group_side_effect(*args, **kwargs):
            if kwargs.get("create"):
                return DummyKadiGroup("created_group")
            return DummyKadiGroup("existing_group")
        self.group.side_effect = group_side_effect

        def record_side_effect(*args, **kwargs):
            if kwargs.get("create"):
                return DummyKadiRecord()
            return DummyKadiRecord()
        self.record.side_effect = record_side_effect

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class DummyUI:
    def __init__(self):
        self.error_shown = None
    def show_error(self, title, message):
        self.error_shown = (title, message)

# --- Fixtures ---

@pytest.fixture
def dummy_ui_instance():
    return DummyUI()

@pytest.fixture
def local_record(tmp_path):
    fake_file = tmp_path / "image.tif"
    fake_file.write_text("dummy image data")
    record = LocalRecord(
        identifier="abc-ipat-sample1",
        sample_name="sample1",
        datatype="tif",
        date="20250405"
    )
    record.files_uploaded[str(fake_file.resolve())] = False
    return record

# --- Unit Tests ---

def test_get_db_user_from_local_record_user_found(dummy_ui_instance, local_record):
    dummy_manager = DummyKadiManager()
    dummy_manager.user = MagicMock(return_value=DummyKadiUser("abc-ipat"))
    sync_mgr = KadiSyncManager(ui=dummy_ui_instance)
    user = sync_mgr._get_db_user_from_local_record(dummy_manager, local_record)
    assert user is not None
    assert user.id == "abc-ipat"

def test_get_db_user_from_local_record_user_not_found(dummy_ui_instance, local_record):
    dummy_manager = DummyKadiManager()
    dummy_manager.user = MagicMock(side_effect=Exception("User not found"))
    sync_mgr = KadiSyncManager(ui=dummy_ui_instance)
    user = sync_mgr._get_db_user_from_local_record(dummy_manager, local_record)
    assert user is None
    assert dummy_ui_instance.error_shown is not None
    title, message = dummy_ui_instance.error_shown
    assert "User" in title or "User" in message
    assert "not found" in title or "not found" in message

def test_get_or_create_db_user_group_existing(dummy_ui_instance, local_record):
    dummy_manager = DummyKadiManager()
    dummy_manager.group = MagicMock(return_value=DummyKadiGroup("existing_group"))
    sync_mgr = KadiSyncManager(ui=dummy_ui_instance)
    user = DummyKadiUser("abc-ipat")
    group = sync_mgr._get_or_create_db_user_rawdata_group(dummy_manager, local_record, user)
    assert group.id == "existing_group"

def test_get_or_create_db_user_group_create(dummy_ui_instance, local_record):
    def group_side_effect(*args, **kwargs):
        if kwargs.get("create"):
            return DummyKadiGroup("created_group")
        raise Exception("Not found")
    dummy_manager = DummyKadiManager()
    dummy_manager.group = MagicMock(side_effect=group_side_effect)
    sync_mgr = KadiSyncManager(ui=dummy_ui_instance)
    user = DummyKadiUser("abc-ipat")
    group = sync_mgr._get_or_create_db_user_rawdata_group(dummy_manager, local_record, user)
    assert group.id == "created_group"

def test_get_or_create_db_record(dummy_ui_instance, local_record):
    dummy_manager = DummyKadiManager()
    sync_mgr = KadiSyncManager(ui=dummy_ui_instance)
    record = sync_mgr._get_or_create_db_record(dummy_manager, local_record)
    assert record is not None
    assert hasattr(record, "meta")
    dummy_manager.record.assert_any_call(create=True, identifier=local_record.identifier)

def test_initialize_new_db_record(dummy_ui_instance, local_record):
    dummy_record = DummyKadiRecord()
    dummy_record.set_attribute = MagicMock()
    dummy_record.add_tag = MagicMock()
    dummy_record.link_record = MagicMock()
    dummy_record.add_group_role = MagicMock()
    dummy_record.add_user = MagicMock()

    sync_mgr = KadiSyncManager(ui=dummy_ui_instance)
    local_record.is_in_db = False
    user = DummyKadiUser("abc-ipat")
    device_user = DummyKadiUser("device_user")
    user_group = DummyKadiGroup("user_group")
    device_group = DummyKadiGroup("device_group")

    sync_mgr._initialize_new_db_record(local_record, dummy_record, user, device_user, user_group, device_group)

    dummy_record.set_attribute.assert_any_call('title', local_record.sample_name)
    dummy_record.set_attribute.assert_any_call('description', DEFAULT_REM_RECORD_DESCRIPTION)
    dummy_record.set_attribute.assert_any_call('type', 'rawdata')
    dummy_record.add_tag.assert_any_call('Electron Microscopy')
    dummy_record.add_tag.assert_any_call(local_record.datatype)
    dummy_record.link_record.assert_called_with(DEVICE_RECORD_ID, 'generated by')
    assert dummy_record.add_group_role.call_count >= 2
    dummy_record.add_user.assert_any_call(user_id=device_user.id, role_name='admin')
    dummy_record.add_user.assert_any_call(user_id=user.id, role_name='admin')

def test_upload_record_files_success(dummy_ui_instance):
    record = LocalRecord(identifier="abc-ipat-sample1", sample_name="sample1", datatype="tif", date="20250405")
    record.files_uploaded = {
        "/dummy/path/file1.tif": False,
        "/dummy/path/file2.tif": False,
    }
    dummy_record = DummyKadiRecord()
    dummy_record.upload_file = MagicMock(side_effect=lambda path, force=False: dummy_record.uploaded_files.append((path, force)))
    sync_mgr = KadiSyncManager(ui=dummy_ui_instance)
    sync_mgr._upload_record_files(dummy_record, record)

    for status in record.files_uploaded.values():
        assert status is True
    assert len(dummy_record.uploaded_files) == 2

def test_upload_record_files_missing_file(dummy_ui_instance):
    record = LocalRecord(identifier="abc-ipat-sample1", sample_name="sample1", datatype="tif", date="20250405")
    record.files_uploaded = {
        "/dummy/path/file1.tif": False,
        "/dummy/path/file2.tif": False,
    }
    dummy_record = DummyKadiRecord()
    def upload_file_side_effect(path, force=False):
        if "file1.tif" in path:
            raise FileNotFoundError
        dummy_record.uploaded_files.append((path, force))
    dummy_record.upload_file = MagicMock(side_effect=upload_file_side_effect)
    sync_mgr = KadiSyncManager(ui=dummy_ui_instance)
    sync_mgr._upload_record_files(dummy_record, record)

    assert "/dummy/path/file1.tif" not in record.files_uploaded
    assert record.files_uploaded["/dummy/path/file2.tif"] is True
    assert len(dummy_record.uploaded_files) == 1
