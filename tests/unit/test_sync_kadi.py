import pytest
from unittest.mock import MagicMock, patch

from ipat_watchdog.core.sync.sync_kadi import KadiSyncManager
from ipat_watchdog.core.records.local_record import LocalRecord


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
        self.record.side_effect = lambda *args, **kwargs: DummyKadiRecord()

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
def local_record(tmp_path, tmp_settings):
    # tmp_settings ensures SettingsStore is initialized before LocalRecord.__post_init__
    fake_file = tmp_path / "image.tif"
    fake_file.write_text("dummy image data")
    record = LocalRecord(
        identifier="abc-ipat-sample1",
        sample_name="sample1",
        datatype="tif",
        date="20250405",
    )
    record.files_uploaded[str(fake_file.resolve())] = False
    return record


@pytest.fixture
def sync_mgr(fake_ui, tmp_settings, monkeypatch):
    # Monkey-patch KadiManager inside the module under test
    import ipat_watchdog.core.sync.sync_kadi as _mod
    monkeypatch.setattr(_mod, "KadiManager", DummyKadiManager)
    
    # Ensure device context is set for settings manager
    from ipat_watchdog.core.config.settings_store import SettingsStore
    settings_manager = SettingsStore.get_manager()
    if hasattr(settings_manager, '_devices'):
        for device in settings_manager._devices.values():
            if device.get_device_id() == "test_device":
                settings_manager.set_current_device(device)
                break
    
    return KadiSyncManager(ui=fake_ui, settings_manager=settings_manager)


def test_get_db_user_from_local_record_user_found(sync_mgr, local_record):
    dummy_mgr = DummyKadiManager()
    dummy_mgr.user.return_value = DummyKadiUser("abc-ipat")
    user = sync_mgr._get_db_user_from_local_record(dummy_mgr, local_record)
    assert user.id == "abc-ipat"


def test_get_db_user_from_local_record_user_not_found(sync_mgr, fake_ui, local_record):
    dummy_mgr = DummyKadiManager()
    dummy_mgr.user.side_effect = Exception("User not found")
    user = sync_mgr._get_db_user_from_local_record(dummy_mgr, local_record)
    assert user is None
    # HeadlessUI records errors in .errors
    assert fake_ui.errors


def test_get_or_create_db_user_group_existing(sync_mgr, local_record):
    dummy_mgr = DummyKadiManager()
    dummy_mgr.group.return_value = DummyKadiGroup("existing_group")
    user = DummyKadiUser("abc-ipat")
    group = sync_mgr._get_or_create_db_user_rawdata_group(dummy_mgr, local_record, user)
    assert group.id == "existing_group"


def test_get_or_create_db_user_group_create(sync_mgr, local_record):
    def side_effect(*args, **kwargs):
        if kwargs.get("create"):
            return DummyKadiGroup("created_group")
        raise Exception("Group not found")

    dummy_mgr = DummyKadiManager()
    dummy_mgr.group.side_effect = side_effect
    user = DummyKadiUser("abc-ipat")
    group = sync_mgr._get_or_create_db_user_rawdata_group(dummy_mgr, local_record, user)
    assert group.id == "created_group"


def test_get_or_create_db_record(sync_mgr, local_record):
    dummy_mgr = DummyKadiManager()
    record = sync_mgr._get_or_create_db_record(dummy_mgr, local_record.identifier)
    assert record is not None
    dummy_mgr.record.assert_any_call(create=True, identifier=local_record.identifier)


def test_initialize_new_db_record(sync_mgr, local_record):
    dummy_record = DummyKadiRecord()
    dummy_record.set_attribute = MagicMock()
    dummy_record.add_tag = MagicMock()
    dummy_record.link_record = MagicMock()
    dummy_record.add_group_role = MagicMock()
    dummy_record.add_user = MagicMock()

    local_record.is_in_db = False
    user = DummyKadiUser("abc-ipat")
    device_user = DummyKadiUser("device_user")
    user_group = DummyKadiGroup("user_group")
    device_group = DummyKadiGroup("device_group")
    sync_mgr._initialize_new_db_record(
        local_record,
        dummy_record,
        user,
        device_user,
        user_group,
        device_group,
    )

    dummy_record.set_attribute.assert_any_call("title", local_record.sample_name)
    dummy_record.set_attribute.assert_any_call(
        "description", None
    )
    dummy_record.set_attribute.assert_any_call("type", "rawdata")
    dummy_record.link_record.assert_called_with(
        device_user.id, "generated by"
    )
    dummy_record.add_user.assert_any_call(user_id=user.id, role_name="admin")


def test_upload_record_files_success(sync_mgr):
    record = LocalRecord(
        identifier="abc-ipat-sample1",
        sample_name="sample1",
        datatype="tif",
        date="20250405",
    )
    record.files_uploaded = {
        "/dummy/path/file1.tif": False,
        "/dummy/path/file2.tif": False,
    }
    dummy_record = DummyKadiRecord()
    dummy_record.upload_file = MagicMock()

    sync_mgr._upload_record_files(dummy_record, record)

    # All statuses should become True
    assert all(record.files_uploaded.values())
    assert dummy_record.upload_file.call_count == 2


def test_upload_record_files_missing(sync_mgr):
    record = LocalRecord(
        identifier="abc-ipat-sample1",
        sample_name="sample1",
        datatype="tif",
        date="20250405",
    )
    record.files_uploaded = {
        "/dummy/path/file1.tif": False,
        "/dummy/path/file2.tif": False,
    }
    dummy_record = DummyKadiRecord()

    def upload_side_effect(path, force=False):
        if "file1" in path:
            raise FileNotFoundError
        dummy_record.uploaded_files.append((path, force))

    dummy_record.upload_file = MagicMock(side_effect=upload_side_effect)

    sync_mgr._upload_record_files(dummy_record, record)

    # file1 should be removed, file2 marked True
    assert "/dummy/path/file1.tif" not in record.files_uploaded
    assert record.files_uploaded["/dummy/path/file2.tif"] is True


def test_upload_record_files_returns_false_when_all_missing(sync_mgr):
    record = LocalRecord(identifier="abc-ipat-sample1")
    record.files_uploaded = {
        "/dummy/path/missing1.tif": False,
        "/dummy/path/missing2.tif": False,
    }
    dummy_record = DummyKadiRecord()
    dummy_record.upload_file = MagicMock(side_effect=FileNotFoundError)

    result = sync_mgr._upload_record_files(dummy_record, record)

    assert result is False
    assert record.files_uploaded == {}