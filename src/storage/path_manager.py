"""
path_manager.py

This module defines the PathManager class, which handles the construction and validation
of file and directory paths within the application. It ensures that all necessary directories
exist, sanitizes user inputs to conform to naming conventions, and generates unique filenames
to prevent conflicts.
"""

import os

from src.records.local_record import LocalRecord
from src.config.settings import RECORD_DIR, RENAME_DIR, EXCEPTIONS_DIR, FILENAME_PATTERN, ID_SEP
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

    @staticmethod
    def init_dirs():
        # Ensure all required directories exist; create them if they don't
        for directory in [RECORD_DIR, RENAME_DIR, EXCEPTIONS_DIR]:
            os.makedirs(directory, exist_ok=True)

    @staticmethod
    def sanitize_and_validate_name(filename_prefix: str) -> tuple:
        """
        Validates and sanitizes a base name against the naming convention.
        Expected format: 'UserID-Institute-SampleID'
        
        Constraints:
            - Institute: letters only
            - UserID: letters only
            - SampleID: Lower-case alphanumeric and underscores

        Args:
            filename_prefix (str): The original filename prefix to validate.

        Returns:
            Tuple[str, bool]:
                - A possibly sanitized version of the filename_prefix
                - A boolean indicating if the name is valid
        """
        # Quick overall pattern check (if you use a compiled regex for the entire string)
        if not FILENAME_PATTERN.match(filename_prefix):
            return filename_prefix, False

        # extract the inst and user_id as the first two parts of the filename
        parts = filename_prefix.split(ID_SEP)
        user_id, institute = parts[:2]

        # the sample_id is the rest of the filename
        sample_id = ID_SEP.join(parts[2:])

        sample_id = sample_id.replace(' ', '_')

        # Rebuild and return sanitized name
        sanitized = f"{user_id.lower()}{ID_SEP}{institute.lower()}{ID_SEP}{sample_id}"
        return sanitized, True
    
    @classmethod
    def validate_user_input(cls, dialog_result: dict) -> tuple:
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
        
        user_ID =   dialog_result.get('name')
        institute = dialog_result.get('institute')
        sample_ID = dialog_result.get('sample_ID')

        # Check that all required fields are provided
        if not (user_ID and institute and sample_ID):
            return "All fields are required.", False

        # Combine into the expected "institute_userID_sampleID" format
        original_name = f"{user_ID}{ID_SEP}{institute}{ID_SEP}{sample_ID}"
        sanitized_name, is_valid = cls.sanitize_and_validate_name(original_name)
        if not is_valid:
            return "Invalid Parts", False

        return sanitized_name, True
    
    @staticmethod
    def get_record_path(record: LocalRecord) -> str:
        """
        Returns the directory path for a given record based on its long_id.
        """
        return os.path.join(RECORD_DIR, record.identifier)


    @classmethod
    def get_rename_path(cls, name: str) -> str:
        """
        Returns a unique path in the rename directory.
        """
        filename_prefix, extension = os.path.splitext(name)
        return cls.get_unique_filename(RENAME_DIR, filename_prefix, extension)

    @classmethod
    def get_exception_path(cls, name: str) -> str:
        """
        Returns a unique path in the exceptions directory.
        """
        filename_prefix, extension = os.path.splitext(name)
        return cls.get_unique_filename(EXCEPTIONS_DIR, filename_prefix, extension)
    
    @staticmethod
    def get_unique_filename(directory: str, filename_prefix: str, extension: str) -> str:
        """
        Generates a unique filename in the given directory by appending a counter if needed.
        """
        counter = 1
        while True:
            candidate = f"{filename_prefix}{ID_SEP}{counter:02d}{extension}"

            unique_path = os.path.join(directory, candidate)
            if not os.path.exists(unique_path):
                return unique_path
            counter += 1
    