"""Centralised helpers for routing failed artefacts to the exception bucket."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ipat_watchdog.core.interactions import (UserInteractionPort,
                                             WarningMessages)
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.storage.filesystem_utils import \
    move_to_exception_folder

logger = setup_logger(__name__)


def safe_move_to_exception(path_like: str, prefix: str | None = None, extension: str | None = None) -> None:
    """Attempt to move the artefact into the exception folder while masking IO errors."""
    try:
        filename_prefix: str = prefix if prefix is not None else ""
        file_extension: str = extension if extension is not None else ""
        move_to_exception_folder(path_like, filename_prefix, file_extension)
    except FileNotFoundError:
        logger.debug("Path already removed while moving to exceptions: %s", path_like)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Failed to move %s to exceptions: %s", path_like, exc)


def move_to_exception_and_inform(
    interactions: UserInteractionPort,
    src_path: str,
    prefix: str,
    extension: str,
    severity: str,
    message: str,
    preprocessed_src_path: Optional[str] = None,
) -> None:
    """Move the item to exceptions (including staged copies) and notify the user."""
    safe_move_to_exception(src_path, prefix, extension)

    if (
        preprocessed_src_path
        and preprocessed_src_path != src_path
        and Path(preprocessed_src_path).exists()
    ):
        safe_move_to_exception(preprocessed_src_path, prefix, extension)

    severity_lower = severity.lower()
    if severity_lower == "warning":
        interactions.show_warning(severity, message)
    else:
        interactions.show_error(severity, message)


def handle_invalid_datatype(
    interactions: UserInteractionPort,
    src_path: str,
    filename_prefix: str,
    extension: str,
) -> None:
    """Standard path for unsupported datatypes."""
    move_to_exception_and_inform(
        interactions,
        src_path,
        filename_prefix,
        extension,
        severity="Warning",
        message=WarningMessages.INVALID_DATA_TYPE_DETAILS,
    )
