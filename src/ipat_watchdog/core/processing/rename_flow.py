"""
Rename flow helpers: interactive dialog to correct invalid filenames and
retry routing after a successful rename.
"""
from __future__ import annotations

from typing import Callable, Optional
from pathlib import Path

from ipat_watchdog.core.ui.ui_abstract import UserInterface
from ipat_watchdog.core.ui.ui_messages import InfoMessages
from ipat_watchdog.core.storage.filesystem_utils import (
    move_to_rename_folder,
    explain_filename_violation,
    analyze_user_input,
)


def interactive_rename_loop(
    ui: UserInterface,
    filename_prefix: str,
    contextual_reason: Optional[str] = None,
) -> Optional[str]:
    """
    Interactive loop for getting valid filename from user.

    Returns sanitized prefix or None if user cancels.
    """
    attempted = filename_prefix
    last_analysis = explain_filename_violation(attempted)
    if contextual_reason:
        last_analysis["reasons"].insert(0, contextual_reason)

    while True:
        user_input = ui.show_rename_dialog(attempted, last_analysis)
        if user_input is None:
            return None
        analysis = analyze_user_input(user_input)
        if analysis["valid"]:
            return analysis["sanitized"]
        attempted = f"{user_input.get('name', '')}-{user_input.get('institute', '')}-{user_input.get('sample_ID', '')}"
        last_analysis = analysis


def rename_flow_controller(
    ui: UserInterface,
    get_processor_for_file: Callable[[str], object],
    route_item: Callable[[str, str, str, object], None],
    src_path: str,
    filename_prefix: str,
    extension: str,
    contextual_reason: Optional[str] = None,
) -> None:
    """
    Manage the interactive rename flow and retry routing when successful.
    """
    new_prefix = interactive_rename_loop(ui, filename_prefix, contextual_reason)
    if new_prefix is not None:
        try:
            file_processor = get_processor_for_file(src_path)
            route_item(src_path, new_prefix, extension, file_processor)
        except Exception as e:
            # If retrying fails, move item to rename folder for manual handling
            move_to_rename_folder(src_path, filename_prefix, extension)
            ui.show_error("Processing Error", f"Unable to process file: {e}")
        return

    # User cancelled rename - move to rename folder for manual handling
    move_to_rename_folder(src_path, filename_prefix, extension)
    ui.show_info(InfoMessages.OPERATION_CANCELLED, InfoMessages.MOVED_TO_RENAME)
