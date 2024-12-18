import os
import re
import datetime
from typing import List, Tuple

from src.records.local_record import RecordInfo, LocalRecord
from src.config.settings import ARCHIVE_DIR, STAGING_DIR, RENAME_DIR, EXCEPTIONS_DIR, FILENAME_PATTERN, DEVICE_ID

class PathManager:
    def __init__(self):
        self.archive_dir = ARCHIVE_DIR
        self.staging_dir = STAGING_DIR
        self.rename_dir = RENAME_DIR
        self.exceptions_dir = EXCEPTIONS_DIR
        self.naming_pattern = FILENAME_PATTERN

        self.device_id = DEVICE_ID

        # Ensure all directories exist
        for directory in [self.archive_dir, self.staging_dir, self.rename_dir, self.exceptions_dir]:
            os.makedirs(directory, exist_ok=True)

    def scrub_input(self, input_str: str) -> str:
        """Sanitize input string to conform to naming conventions."""
        return re.sub(r'[^A-Za-z0-9_-]+', '_', input_str)

    def validate_naming_convention(self, base_name: str) -> bool:
        """Check if the base name matches the naming convention."""
        return bool(self.naming_pattern.match(base_name))
    
    def validate_user_input(self, dialog_result):
        if dialog_result is None:
            return False, "User cancelled the dialog."

        user_ID = dialog_result['name']
        institute = dialog_result['institute']
        sample_ID = dialog_result['sample_ID']

        if not user_ID or not institute or not sample_ID:
            return False, "All fields are required."
        return True, (user_ID, institute, sample_ID)

    def construct_long_id(self, id_info: RecordInfo) -> str:
        """Construct the long_id using RecordIdInfo."""
        return f"{id_info.device_id}-{id_info.date}-REC_{id_info.daily_record_count:03}-{id_info.data_type}-{id_info.institute}-{id_info.user_id}"

    def construct_short_id(self, id_info: RecordInfo) -> str:
        """Construct the short_id using RecordIdInfo."""
        return f"{id_info.institute}_{id_info.user_id}_{id_info.sample_id}"

    def get_record_path(self, record: LocalRecord) -> str:
        """Get the archive directory path for a given record."""
        return os.path.join(self.archive_dir, record.long_id)

    def get_staging_path(self, filename: str) -> str:
        """Get the full path in the staging directory for a given filename."""
        return os.path.join(self.staging_dir, filename)

    def get_rename_path(self, name: str) -> str:
        """Generate a unique rename path for a given name."""
        return self._generate_unique_path(self.rename_dir, name)

    def get_exception_path(self, name: str) -> str:
        """Generate a path in the exceptions directory for a given name."""
        return self._generate_unique_path(self.exceptions_dir, name)

    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str:
        """Generate a unique filename within a specified directory."""
        counter = 1
        unique_name = f"{base_name}_{counter}{extension}"
        unique_path = os.path.join(directory, unique_name)

        while os.path.exists(unique_path):
            unique_name = f"{base_name}_{counter}{extension}"
            unique_path = os.path.join(directory, unique_name)
            counter += 1

        return unique_path

    def _generate_unique_path(self, directory: str, name: str) -> str:
        """Helper method to generate a unique file or folder path within a directory."""
        base_name, extension = os.path.splitext(name)
        unique_path = self.get_unique_filename(directory, base_name, extension)
        return unique_path

    def construct_new_file_path(
        self, 
        id_info: RecordInfo, 
        extension: str, 
        existing_basenames: List[str]
    ) -> Tuple[str, str]:
        """
        Construct a unique file path based on RecordIdInfo and extension.
        
        Returns:
            Tuple containing the new base name and the full file path.
        """
        base_directory = self.get_record_path(id_info)
        os.makedirs(base_directory, exist_ok=True)

        base_name = self.construct_short_id(id_info)
        base_name = self.scrub_input(base_name)

        # Ensure uniqueness
        unique_path = self.get_unique_filename(base_directory, base_name, extension)
        unique_base_name = os.path.basename(unique_path)

        return unique_base_name, unique_path

    def parse_long_id(self, long_id: str) -> RecordInfo:
        """
        Parse a long_id string back into a RecordIdInfo object.
        
        Expected format: "{device_id}-{date}-REC_{daily_record_count}-{institute}-{user_id}"
        """
        pattern = r'^(?P<device_id>[A-Za-z0-9_-]+)-(?P<date>\d{8})-REC_(?P<daily_record_count>\d{3})-(?P<institute>[A-Za-z0-9_-]+)-(?P<user_id>[A-Za-z0-9_-]+)$'
        match = re.match(pattern, long_id)
        if not match:
            raise ValueError(f"Invalid long_id format: {long_id}")

        id_info = RecordInfo(
            device_id=match.group('device_id'),
            date=match.group('date'),
            daily_record_count=int(match.group('daily_record_count')),
            data_type="",  # Data type might need to be inferred or stored separately
            institute=match.group('institute'),
            user_id=match.group('user_id'),
            sample_id=""  # Sample ID is not included in long_id; handle accordingly
        )
        return id_info
    
    def generate_new_record_info(self, base_name: str, data_type: str, record_count: int) -> Tuple[str, RecordInfo, str]:
        current_date = datetime.datetime.now().strftime('%Y%m%d')
        institute, user_ID, sample_ID = base_name.split('_')
        
        record_info = RecordInfo(
            device_id=self.device_id,
            date=current_date,
            daily_record_count=record_count+1,
            data_type=data_type,
            institute=institute,
            user_id=user_ID,
            sample_id=sample_ID
        )
        
        return record_info
    
    def generate_file_id(self, base_name) -> str:
        device_name = self.device_id.split('_')[0]
        current_date = datetime.datetime.now().strftime('%Y%m%d')
        institute, user_ID, sample_ID = base_name.split('_')

        return f"{device_name}_{institute}_{user_ID}_{sample_ID}_{current_date}"
    