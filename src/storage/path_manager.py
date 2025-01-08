"""
path_manager.py

This module defines the PathManager class, which handles the construction and validation
of file and directory paths within the application. It ensures that all necessary directories
exist, sanitizes user inputs to conform to naming conventions, and generates unique filenames
to prevent conflicts.
"""

import os

from src.records.local_record import LocalRecord
from src.config.settings import RECORD_DIR, RENAME_DIR, EXCEPTIONS_DIR, FILENAME_PATTERN
from src.app.logger import setup_logger

logger = setup_logger(__name__)

class PathManager:
    """
    The PathManager class manages file and directory paths used in the application.
    
    Responsibilities:
        - Ensures required directories exist.
        - Sanitizes and validates user inputs to adhere to naming conventions.
        - Generates unique filenames to avoid naming conflicts.
        - Constructs paths for records, renaming operations, and exception handling.
    """
    
    def __init__(self):
        """
        Initializes the PathManager by setting up directory paths and ensuring their existence.
        """
        self.record_dir = RECORD_DIR
        self.rename_dir = RENAME_DIR
        self.exceptions_dir = EXCEPTIONS_DIR
        self.naming_pattern = FILENAME_PATTERN

        # Ensure all required directories exist; create them if they don't
        for directory in [self.record_dir, self.rename_dir, self.exceptions_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def sanitize_and_validate_name(self, base_name: str) -> tuple:
        """
        Validates and sanitizes a base name against the naming convention.
        Expected format: 'Institute_UserID_SampleID'
        
        Constraints:
            - Institute: letters only
            - UserID: letters only
            - SampleID: letters, numbers, or hyphens
            - Any spaces in the sample ID are replaced with hyphens.

        Args:
            base_name (str): The original base name to validate.

        Returns:
            Tuple[str, bool]:
                - A possibly sanitized version of the base_name
                - A boolean indicating if the name is valid
        """
        # Quick overall pattern check (if you use a compiled regex for the entire string)
        if not self.naming_pattern.match(base_name):
            return base_name, False

        # Attempt to split into exactly three parts
        parts = base_name.split('_')
        if len(parts) != 3:
            return base_name, False

        institute, user_id, sample_id = parts
        # Replace spaces with hyphens in sample_id
        sample_id = sample_id.replace(' ', '-')

        # Rebuild and return sanitized name
        sanitized = f"{institute}_{user_id}_{sample_id}"
        return sanitized, True
    
    def validate_user_input(self, dialog_result: dict) -> tuple:
        """
        Validates the user input collected from the dialog.
        
        Args:
            dialog_result (dict or None): The result from the dialog containing user inputs.
                Expected keys: 'name', 'institute', 'sample_ID'
        
        Returns:
            Tuple[Any, bool]:
                - (error_message, False) if invalid, or
                - (sanitized_base_name, True) if valid
        """
        if dialog_result is None:
            return "User cancelled the dialog.", False
        
        user_ID = dialog_result.get('name')
        institute = dialog_result.get('institute')
        sample_ID = dialog_result.get('sample_ID')

        # Check that all required fields are provided
        if not (user_ID and institute and sample_ID):
            return "All fields are required.", False

        # Combine into the expected "institute_userID_sampleID" format
        original_name = f"{institute}_{user_ID}_{sample_ID}"
        sanitized_name, is_valid = self.sanitize_and_validate_name(original_name)
        if not is_valid:
            return "Invalid Parts", False

        return sanitized_name, True
      
    def get_record_path(self, record: LocalRecord) -> str:
        """
        Returns the directory path for a given record based on its long_id.
        """
        return os.path.join(self.record_dir, record.long_id)

    def get_rename_path(self, name: str) -> str:
        """
        Returns a unique path in the rename directory.
        """
        base_name, extension = os.path.splitext(name)
        return self.get_unique_filename(self.rename_dir, base_name, extension)

    def get_exception_path(self, name: str) -> str:
        """
        Returns a unique path in the exceptions directory.
        """
        base_name, extension = os.path.splitext(name)
        return self.get_unique_filename(self.exceptions_dir, base_name, extension)

    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str:
        """
        Generates a unique filename in the given directory by appending a counter if needed.
        """
        counter = 1
        while True:
            candidate = f"{base_name}_{counter}{extension}"

            unique_path = os.path.join(directory, candidate)
            if not os.path.exists(unique_path):
                return unique_path
            counter += 1
    