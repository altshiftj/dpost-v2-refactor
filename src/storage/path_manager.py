import os
import re
import datetime
from typing import List, Tuple

from src.records.local_record import RecordInfo, LocalRecord
from src.config.settings import RECORD_DIR, RENAME_DIR, EXCEPTIONS_DIR, FILENAME_PATTERN

class PathManager:
    def __init__(self):
        self.record_dir = RECORD_DIR
        self.rename_dir = RENAME_DIR
        self.exceptions_dir = EXCEPTIONS_DIR
        self.naming_pattern = FILENAME_PATTERN

        # Ensure all directories exist
        for directory in [self.record_dir, self.rename_dir, self.exceptions_dir]:
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

    def get_record_path(self, record: LocalRecord) -> str:
        """Get the directory path for a given record."""
        return os.path.join(self.record_dir, record.long_id)

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
