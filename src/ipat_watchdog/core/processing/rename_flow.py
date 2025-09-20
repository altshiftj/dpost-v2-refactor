"""Interactive rename flow used when filenames fail validation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Optional

from ipat_watchdog.core.storage.filesystem_utils import (
    analyze_user_input,
    explain_filename_violation,
    move_to_rename_folder,
)
from ipat_watchdog.core.ui.ui_abstract import UserInterface
from ipat_watchdog.core.ui.ui_messages import InfoMessages

try:  # pragma: no cover - importing from tkinter is optional in tests
    from tkinter import TclError  # type: ignore
except Exception:  # pragma: no cover
    class TclError(Exception):
        pass


@dataclass
class RenameOutcome:
    """Result of running the interactive rename flow."""

    sanitized_prefix: Optional[str]
    cancelled: bool = False


class RenameService:
    """Owns the rename dialog loop and follow-up actions."""

    def __init__(self, ui: UserInterface) -> None:
        self._ui = ui

    def obtain_valid_prefix(
        self,
        current_prefix: str,
        contextual_reason: Optional[str] = None,
    ) -> RenameOutcome:
        attempted = current_prefix
        last_analysis = explain_filename_violation(attempted)
        if contextual_reason:
            last_analysis["reasons"].insert(0, contextual_reason)

        while True:
            try:
                user_input = self._ui.show_rename_dialog(attempted, last_analysis)
            except TclError:
                sleep(0.05)
                continue

            if user_input is None:
                return RenameOutcome(sanitized_prefix=None, cancelled=True)

            analysis = analyze_user_input(user_input)
            if analysis["valid"]:
                return RenameOutcome(sanitized_prefix=analysis["sanitized"], cancelled=False)

            attempted = self._compose_attempted_prefix(user_input)
            last_analysis = analysis

    def send_to_manual_bucket(self, src_path: str, filename_prefix: str, extension: str) -> None:
        move_to_rename_folder(src_path, filename_prefix, extension)
        self._ui.show_info(InfoMessages.OPERATION_CANCELLED, InfoMessages.MOVED_TO_RENAME)

    @staticmethod
    def _compose_attempted_prefix(user_input: dict) -> str:
        return "-".join(
            (
                user_input.get("name", ""),
                user_input.get("institute", ""),
                user_input.get("sample_ID", ""),
            )
        )
