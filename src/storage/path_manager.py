"""
path_manager.py

This module defines the PathManager class, which handles the construction and validation
of file and directory paths within the application. It ensures that all necessary directories
exist, sanitizes user inputs to conform to naming conventions, and generates unique filenames
to prevent conflicts.
"""

import os
import re
import datetime
from typing import List, Tuple

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
            # Log the creation or confirmation of directory existence if needed
    
    def scrub_input(self, input_str: str) -> str: # TODO Implement this method
        """
        Sanitizes the input string to conform to naming conventions by replacing
        invalid characters with underscores.
        
        Args:
            input_str (str): The input string to sanitize.
        
        Returns:
            str: The sanitized string.
        """
        # Replace any character that is not a letter, number, underscore, or hyphen with an underscore
        sanitized = re.sub(r'[^A-Za-z0-9_-]+', '_', input_str)
        logger.debug(f"Sanitized input: {input_str} -> {sanitized}")
        return sanitized
    
    def validate_naming_convention(self, base_name: str) -> bool:
        """
        Validates whether the provided base name matches the predefined naming convention.
        
        Args:
            base_name (str): The base name to validate.
        
        Returns:
            bool: True if the base name matches the naming convention, False otherwise.
        """
        return bool(self.naming_pattern.match(base_name))
    
    def validate_user_input(self, dialog_result):
        """
        Validates the user input collected from the dialog.
        
        Args:
            dialog_result (dict or None): The result from the dialog containing user inputs.
        
        Returns:
            Tuple[bool, str or Tuple[str, str, str]]: 
                - A boolean indicating if the input is valid.
                - An error message string if invalid, or a tuple of validated inputs.
        """
        if dialog_result is None:
            return False, "User cancelled the dialog."
        
        user_ID = dialog_result['name']
        institute = dialog_result['institute']
        sample_ID = dialog_result['sample_ID']

        # Check that all required fields are provided
        if not user_ID or not institute or not sample_ID:
            return False, "All fields are required."
        return True, (user_ID, institute, sample_ID)
    
    def get_record_path(self, record: LocalRecord) -> str:
        """
        Constructs the directory path for a given record based on its long_id.
        
        Args:
            record (LocalRecord): The record for which to get the directory path.
        
        Returns:
            str: The full path to the record's directory.
        """
        return os.path.join(self.record_dir, record.long_id)
    
    def get_rename_path(self, name: str) -> str:
        """
        Generates a unique path in the rename directory for a given name to prevent conflicts.
        
        Args:
            name (str): The base name for the rename operation.
        
        Returns:
            str: A unique path within the rename directory.
        """
        return self._generate_unique_path(self.rename_dir, name)
    
    def get_exception_path(self, name: str) -> str:
        """
        Generates a unique path in the exceptions directory for handling exceptions related to a name.
        
        Args:
            name (str): The base name associated with the exception.
        
        Returns:
            str: A unique path within the exceptions directory.
        """
        return self._generate_unique_path(self.exceptions_dir, name)
    
    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str:
        """
        Generates a unique filename within a specified directory by appending a counter
        if a file with the same name already exists.
        
        Args:
            directory (str): The directory in which to create the file.
            base_name (str): The base name for the file.
            extension (str): The file extension (e.g., '.txt').
        
        Returns:
            str: A unique filename within the directory.
        """
        counter = 1
        unique_name = f"{base_name}_{counter}{extension}"
        unique_path = os.path.join(directory, unique_name)

        # Increment the counter until a unique filename is found
        while os.path.exists(unique_path):
            unique_name = f"{base_name}_{counter}{extension}"
            unique_path = os.path.join(directory, unique_name)
            counter += 1

        return unique_path
    
    def _generate_unique_path(self, directory: str, name: str) -> str:
        """
        Helper method to generate a unique file or folder path within a specified directory.
        
        Args:
            directory (str): The directory in which to create the path.
            name (str): The base name for the file or folder.
        
        Returns:
            str: A unique path within the directory.
        """
        base_name, extension = os.path.splitext(name)
        unique_path = self.get_unique_filename(directory, base_name, extension)
        return unique_path