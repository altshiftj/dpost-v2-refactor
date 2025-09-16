"""
Error handling helpers for the processing workflow.
"""
from pathlib import Path
from ipat_watchdog.core.ui.ui_abstract import UserInterface
from ipat_watchdog.core.ui.ui_messages import WarningMessages
from ipat_watchdog.core.storage.filesystem_utils import move_to_exception_folder
from ipat_watchdog.core.logging.logger import setup_logger

logger = setup_logger(__name__)


def safe_move_to_exception(path_like: str, prefix: str | None = None, extension: str | None = None):
    """Wrapper around move_to_exception_folder that tolerates missing/removed paths."""
    try:
        move_to_exception_folder(path_like, prefix, extension)
    except FileNotFoundError:
        logger.debug("Path already gone when moving to exceptions: %s", path_like)
    except Exception as e:
        logger.warning("Failed to move %s to exceptions: %s", path_like, e)


def move_to_exception_and_inform(
    ui: UserInterface,
    src_path: str,
    prefix: str,
    extension: str,
    severity: str,
    message: str,
    preprocessed_src_path: str | None = None,
) -> None:
    """
    Move the item to exceptions (file or staging folder) and notify the user.
    If a different preprocessed_src_path exists, move that too.
    """
    safe_move_to_exception(src_path, prefix, extension)

    if (
        preprocessed_src_path
        and preprocessed_src_path != src_path
        and Path(preprocessed_src_path).exists()
    ):
        safe_move_to_exception(preprocessed_src_path, prefix, extension)

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
