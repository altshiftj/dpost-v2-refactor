"""
ui_messages.py

This module centralizes all UI messages used throughout the application.
It organizes messages by category and provides easy access to standardized text
for warnings, errors, information dialogs, and prompts.

Using a centralized message repository makes it easier to:
1. Maintain consistent messaging throughout the application
2. Make application-wide text changes in one place
3. Support localization/internationalization if needed in the future
"""

# ===============================================================================
# Error Messages
# ===============================================================================

class ErrorMessages:
    """Error messages displayed to the user."""
    GENERAL_ERROR = "Error"

    # General errors
    RENAME_FAILED = "Failed to rename: {error}"
    
    # User-related errors
    USER_NOT_FOUND = "User {user_id} not found"
    USER_NOT_FOUND_DETAILS = (
        "User not found in kadi4mat database.\n"
        "Records will be uploaded now and mapped to the\n"
        "{user_id} account when it is created.\n"
        "Please contact the Kadi administrator."
    )

    APPLICATION_ERROR = "Application Error"
    APPLICATION_ERROR_DETAILS = "An unexpected error occurred. Please contact the administrator."
    
    SESSION_END_ERROR = "Session End Error"
    SESSION_END_ERROR_DETAILS = "An error occurred during session end: {error}"

# ===============================================================================
# Warning Messages
# ===============================================================================

class WarningMessages:
    """Warning messages displayed to the user."""
    
    # Data type warnings
    INVALID_DATA_TYPE = "Invalid Data Type"
    INVALID_DATA_TYPE_DETAILS = (
        "The file/folder is not a recognized data type.\n"
        "Only .tif/.tiff images and .elid directories are supported."
    )
    
    # Record-related warnings
    INVALID_RECORD = "Invalid Record"
    INVALID_RECORD_DETAILS = (
        "An existing record with this name cannot be appended.\n"
        "Please create a new record for this data."
    )
    
    # Naming convention warnings
    INVALID_NAME = "Invalid Name"
    INVALID_NAME_DETAILS = (
        "'{filename}{extension}' does not follow the naming convention.\n"
        "Format: User-Institute-Sample_Name\n"
        "No special characters (e.g., !@#$%^&*-+=)\n"
        "30 character limit for Sample Name."
    )
    
    INVALID_CHARACTERS = "Invalid Name"
    INVALID_CHARACTERS_DETAILS = (
        "Please avoid special characters (e.g., !@#$%^&*-+=)\n"
        "30 character limit for Sample Name."
    )
    
    INCOMPLETE_INFO = "Incomplete Information"
    INCOMPLETE_INFO_DETAILS = "All fields are required. Please try again."


# ===============================================================================
# Information Messages
# ===============================================================================

class InfoMessages:
    """Informational messages displayed to the user."""
    
    # Success messages
    SUCCESS = "Success"
    ITEM_RENAMED = "{item_type} renamed to '{filename}'"
    
    # Operation cancelled messages
    OPERATION_CANCELLED = "Operation Cancelled"
    MOVED_TO_RENAME = "The item has been moved to the rename folder."
    
    # New record messages
    NEW_RECORD = "New Record"
    NEW_RECORD_DETAILS = "Please enter a name for the new record."
    
    # Session messages
    SESSION_ACTIVE = "Session Active"
    SESSION_ACTIVE_DETAILS = "A session is in progress. Click 'Done' when finished."


# ===============================================================================
# Dialog Prompts
# ===============================================================================

class DialogPrompts:
    """Text for various dialog prompts in the application."""
    
    # Rename dialog
    RENAME_FILE = "Rename File"
    
    # Record prompts
    APPEND_RECORD = "Append to Existing Record"
    APPEND_RECORD_DETAILS = "Record '{record_name}' already exists. Add file to existing record?"
    
    # Entry field placeholders
    PLACEHOLDER_USER_ID = "Ex: mus"
    PLACEHOLDER_INSTITUTE = "Ex: ipat"
    PLACEHOLDER_SAMPLE_ID = "Ex: ivtrap_a01"
    
    # Field labels
    LABEL_NAME = "Name (Initials):"
    LABEL_INSTITUTE = "Institute (Initials):"
    LABEL_SAMPLE_NAME = "Sample Name:"