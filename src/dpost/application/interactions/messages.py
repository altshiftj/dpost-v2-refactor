"""Centralized message catalog for user-facing strings used within interaction flows.
Grouping them here keeps messaging consistent and simplifies future localization.
"""

from dpost.domain.naming.prefix_policy import (
    ValidationMessages as NamingValidationMessages,
)

ValidationMessages = NamingValidationMessages


class ErrorMessages:
    """Error messages displayed to the user."""

    RENAME_FAILED = "Failed to rename: {error}"
    USER_NOT_FOUND = "User {user_id} not found"
    USER_NOT_FOUND_DETAILS = (
        "User not found in kadi4mat database.\n"
        "Records will be uploaded now and mapped to the\n"
        "{user_id} account when it is created.\n"
        "Please contact the Kadi administrator."
    )
    APPLICATION_ERROR = "Application Error"
    APPLICATION_ERROR_DETAILS = (
        "An unexpected error occurred. Please contact the administrator."
    )
    PROCESSING_ERROR = "Processing Error"
    PROCESSING_ERROR_DETAILS = (
        "Failed to process file: {filename}\n"
        "File has been moved to the exception folder.\n"
        "Error: {error}"
    )
    SESSION_END_ERROR = "Session End Error"
    SESSION_END_ERROR_DETAILS = "An error occurred during session end: {error}"
    SYNC_ERROR = "Sync Error"
    SYNC_ERROR_DETAILS = (
        "Failed to sync processed item '{filename}'.\n"
        "Data remains stored locally and will retry on the next sync attempt.\n"
        "Error: {error}"
    )


class WarningMessages:
    """Warning messages displayed to the user."""

    INVALID_DATA_TYPE = "Invalid Data Type"
    INVALID_DATA_TYPE_DETAILS = (
        "The file/folder is not a recognized data type.\n"
        "Only .tif/.tiff images and .elid directories are supported."
    )
    INVALID_RECORD = "Invalid Record"
    INVALID_RECORD_DETAILS = (
        "An existing record with this name cannot be appended.\n"
        "Please create a new record for this data."
    )
    INVALID_NAME = "Invalid Filename"
    INCOMPLETE_INFO = "Incomplete Information"
    INCOMPLETE_INFO_DETAILS = "All fields are required. Please try again."


class InfoMessages:
    """Informational messages displayed to the user."""

    SUCCESS = "Success"
    ITEM_RENAMED = "{item_type} renamed to '{filename}'"
    OPERATION_CANCELLED = "Operation Cancelled"
    MOVED_TO_RENAME = "The item has been moved to the rename folder."
    SESSION_ACTIVE = "Session Active"
    SESSION_ACTIVE_DETAILS = (
        "A session is in progress. Click 'Done' when finished with your experiments."
    )


class DialogPrompts:
    """Text for various dialog prompts in the application."""

    RENAME_FILE = "Rename File"
    RENAME_EXAMPLE = "Example: MuS-inst-Sample_A"
    APPEND_RECORD = "Append to Existing Record"
    APPEND_RECORD_DETAILS = (
        "Record '{record_name}' already exists. Add file to existing record?"
    )
    APPEND_RECORD_CANCEL_CONTEXT = (
        "Record '{record_id}' already exists, but you chose not to append. "
        "Please choose a different name."
    )
    UNAPPENDABLE_RECORD_CONTEXT = (
        "Record '{record_id}' already exists, and cannot be appended. "
        "Please choose a different name."
    )
    PLACEHOLDER_USER_ID = "Ex: mus"
    PLACEHOLDER_INSTITUTE = "Ex: ipat"
    PLACEHOLDER_SAMPLE_ID = "Ex: Sample_a01"
    LABEL_NAME = "Name (Initials):"
    LABEL_INSTITUTE = "Institute (Initials):"
    LABEL_SAMPLE_NAME = "Sample Name:"
