"""
Error handling helpers for the processing workflow.
"""
from ipat_watchdog.core.ui.ui_abstract import UserInterface
from ipat_watchdog.core.ui.ui_messages import WarningMessages
from ipat_watchdog.core.storage.filesystem_utils import move_to_exception_folder


def move_to_exception_and_inform(
    ui: UserInterface,
    src_path: str,
    prefix: str,
    extension: str,
    severity: str,
    message: str,
) -> None:
    """Move the item to exceptions and notify the user."""
    move_to_exception_folder(src_path, prefix, extension)
    if severity.lower() == "warning":
        ui.show_warning(severity, message)
    else:
        ui.show_error(severity, message)


def handle_invalid_datatype(
    ui: UserInterface, src_path: str, filename_prefix: str, extension: str
) -> None:
    """Standard path for unsupported datatypes."""
    move_to_exception_and_inform(
        ui,
        src_path,
        filename_prefix,
        extension,
        severity="Warning",
        message=WarningMessages.INVALID_DATA_TYPE_DETAILS,
    )
