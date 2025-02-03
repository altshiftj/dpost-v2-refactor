import pytest
from unittest.mock import MagicMock, patch

# Adjust these imports to match your actual paths
# For example:
# from src.sync_manager import KadiSyncManager
# from src.records.local_record import LocalRecord

@pytest.fixture
def mock_ui():
    """
    Returns a mock UserInterface (ui) object.
    """
    return MagicMock()

@pytest.fixture
def sample_local_record():
    """
    Returns a sample LocalRecord object for testing.
    """
    # You’ll want to create it with whatever constructor or initial state your app uses
    # Example local record with dummy data:
    local_record = MagicMock()
    local_record.identifier = "rem-jfi-ipat-trace"  # or anything that matches your typical pattern
    local_record.name = "trace"
    local_record.datatype = "TEM"
    local_record.is_in_db = False
    local_record.files_uploaded = {
        "dummy/path/image1.tif": False,
        "dummy/path/image2.tif": True,  # Suppose one file is already marked as uploaded
    }
    return local_record

@pytest.fixture
def sync_manager(mock_ui):
    """
    Returns an instance of KadiSyncManager with a mocked-out KadiManager.
    """
    # We create our KadiSyncManager
    sync_mgr = None
    with patch("src.sync_manager.KadiManager") as MockKadiManager:
        # The 'with patch(...)' ensures that any usage of KadiManager 
        # inside KadiSyncManager is replaced by this mock.
        mock_kadi_manager_instance = MockKadiManager.return_value

        # Optionally, you can configure the mock_kadi_manager_instance with 
        # dummy return values or side effects as needed.
        sync_mgr = KadiSyncManager(ui=mock_ui)

    return sync_mgr

def test_kadi_sync_manager_init(sync_manager, mock_ui):
    """
    Test that KadiSyncManager initializes with a KadiManager instance
    and a UI without error.
    """
    # The fixture sets up sync_manager. 
    # We just check that attributes are set as expected.
    assert sync_manager.ui is mock_ui
    # KadiManager should have been mocked, so no real connection is made.
    assert sync_manager.db_manager is not None

@pytest.mark.parametrize("record_in_db_state", [False, True])
def test_sync_record_to_database_main_flow(sync_manager, sample_local_record, record_in_db_state):
    """
    Test the main flow of sync_record_to_database. This verifies that:
      - The db_manager context is used correctly.
      - The local_record is eventually marked is_in_db = True if all goes well.
    """
    sample_local_record.is_in_db = record_in_db_state

    # We'll patch the private methods individually so we don't rely on them 
    # being correct for this test. Instead, we're focusing on the main flow.
    with patch.object(sync_manager, "_get_db_user") as mock_get_db_user, \
         patch.object(sync_manager, "_get_or_create_db_user_group") as mock_user_group, \
         patch.object(sync_manager, "_get_or_create_db_device_data_group") as mock_device_data_group, \
         patch.object(sync_manager, "_get_or_create_db_record") as mock_db_record_func, \
         patch.object(sync_manager, "_initialize_new_db_record") as mock_init_record, \
         patch.object(sync_manager, "_upload_record_files") as mock_upload_files:

        # Configure any return values needed
        mock_get_db_user.return_value = MagicMock()
        mock_user_group.return_value = MagicMock()
        mock_device_data_group.return_value = MagicMock()
        mock_db_record = MagicMock()
        mock_db_record_func.return_value = mock_db_record

        sync_manager.sync_record_to_database(sample_local_record)

        # The main method should have used all these private calls in sequence:
        mock_get_db_user.assert_called_once()
        mock_user_group.assert_called_once()
        mock_device_data_group.assert_called_once()
        mock_db_record_func.assert_called_once()
        mock_init_record.assert_called_once()
        mock_upload_files.assert_called_once()

        # Finally, verify local_record.is_in_db is set to True if all is well.
        # Even if it was True already, it should remain True.
        assert sample_local_record.is_in_db is True

def test_sync_record_to_database_user_not_found(sync_manager, sample_local_record):
    """
    Test that if _get_db_user fails (user doesn't exist),
    the UI shows an error and we proceed with a None user object.
    """
    # Make _get_db_user raise an exception or return None 
    # to simulate user not found.
    with patch.object(
        sync_manager, "_get_db_user", 
        side_effect=lambda mgr, rec: None  # or raise an Exception
    ), patch.object(sync_manager, "_get_or_create_db_user_group") as mock_user_group:
        sync_manager.sync_record_to_database(sample_local_record)
        # If _get_db_user returns None, we expect the UI to have shown an error
        sync_manager.ui.show_error.assert_called_once()
        # We may also check that _get_or_create_db_user_group still got called 
        # and used None. If your code tries to add the user to the group, 
        # that might behave differently with None.

def test_sync_record_to_database_exception(sync_manager, sample_local_record):
    """
    Test that an exception in the middle of uploading logs the error 
    and re-raises.
    """
    with patch.object(sync_manager, "_get_db_user", side_effect=RuntimeError("DB is down!")), \
         pytest.raises(RuntimeError) as exc_info:
        sync_manager.sync_record_to_database(sample_local_record)

    # Check that the exception message is the one we expect
    assert "DB is down!" in str(exc_info.value)

def test_upload_record_files_removes_missing_files(sync_manager, sample_local_record):
    """
    Test that if a file doesn't exist (FileNotFoundError),
    it is removed from local_record.files_uploaded.
    """
    # We'll isolate testing of this private method.
    # In practice, you often rely on testing it via sync_record_to_database,
    # but let's illustrate direct testing for clarity.
    mock_db_record = MagicMock()
    missing_file = "dummy/path/missing_file.tif"
    sample_local_record.files_uploaded[missing_file] = False

    # We'll patch db_record.upload_file to raise FileNotFoundError 
    # when the missing file is attempted.
    def side_effect_upload(filepath, force=False):
        if filepath == missing_file:
            raise FileNotFoundError

    mock_db_record.upload_file.side_effect = side_effect_upload

    sync_manager._upload_record_files(mock_db_record, sample_local_record)

    # Verify that the missing file was removed from files_uploaded
    assert missing_file not in sample_local_record.files_uploaded
    # The other file(s) remain
    # e.g., "dummy/path/image1.tif" and "dummy/path/image2.tif" are still there

def test_sync_logs_to_database(sync_manager):
    """
    Test sync_logs_to_database, ensuring we open the KadiManager context,
    get the device record, and upload a log file.
    """
    with patch.object(sync_manager.db_manager, "record") as mock_record, \
         patch.object(sync_manager.db_manager, "__enter__", return_value=sync_manager.db_manager) as mock_enter, \
         patch("src.sync_manager.LOG_FILE", "fake_log_path.log"):

        mock_kadi_record = MagicMock()
        mock_record.return_value = mock_kadi_record

        sync_manager.sync_logs_to_database()

        # Ensure we used the context
        mock_enter.assert_called_once()

        # Ensure we called record(...) with the correct device ID
        # This uses the constant DEVICE_RECORD_ID from your code, 
        # which you'd mock or check if needed.
        mock_record.assert_called_once_with(id="device_record_id_goes_here")  # or whatever the constant is

        # Ensure the log file was uploaded
        mock_kadi_record.upload_file.assert_called_once_with("fake_log_path.log", force=True)
