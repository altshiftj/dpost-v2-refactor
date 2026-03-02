"""Interactive rename flow used when filenames fail validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Pattern

from dpost.application.interactions import InfoMessages
from dpost.application.naming.policy import (
    analyze_user_input,
    explain_filename_violation,
)
from dpost.application.ports import RenameDecision, RenamePrompt, UserInteractionPort
from dpost.infrastructure.storage.filesystem_utils import move_to_rename_folder


@dataclass
class RenameOutcome:
    """Result of running the interactive rename flow."""

    sanitized_prefix: Optional[str]
    cancelled: bool = False


class RenameService:
    """Owns the rename dialog loop and follow-up actions."""

    def __init__(self, interactions: UserInteractionPort) -> None:
        self._interactions = interactions

    def obtain_valid_prefix(
        self,
        current_prefix: str,
        contextual_reason: Optional[str] = None,
        *,
        filename_pattern: Pattern[str] | None = None,
        id_separator: str | None = None,
    ) -> RenameOutcome:
        separator = self._require_id_separator(id_separator)
        attempted = current_prefix
        analysis = explain_filename_violation(
            attempted,
            filename_pattern=filename_pattern,
            id_separator=separator,
        )
        reason_hint = contextual_reason

        while True:
            decision = self._request_new_prefix(attempted, analysis, reason_hint)
            reason_hint = None  # contextual hints should only be prepended once

            if decision.cancelled or not decision.values:
                return RenameOutcome(sanitized_prefix=None, cancelled=True)

            analysis = analyze_user_input(
                decision.values,
                filename_pattern=filename_pattern,
                id_separator=separator,
            )
            if analysis["valid"]:
                return RenameOutcome(
                    sanitized_prefix=analysis["sanitized"], cancelled=False
                )

            attempted = self._compose_attempted_prefix(
                decision.values,
                id_separator=separator,
            )

    def send_to_manual_bucket(
        self,
        src_path: str,
        filename_prefix: str,
        extension: str,
        *,
        rename_dir: str | None = None,
        id_separator: str | None = None,
    ) -> None:
        move_to_rename_folder(
            src_path,
            filename_prefix,
            extension,
            base_dir=rename_dir,
            id_separator=id_separator,
        )
        self._interactions.show_info(
            InfoMessages.OPERATION_CANCELLED,
            InfoMessages.MOVED_TO_RENAME,
        )

    def _request_new_prefix(
        self,
        attempted: str,
        analysis: dict,
        contextual_reason: Optional[str],
    ) -> RenameDecision:
        prompt = RenamePrompt(
            attempted_prefix=attempted,
            analysis=analysis,
            contextual_reason=contextual_reason,
        )
        return self._interactions.request_rename(prompt)

    @staticmethod
    def _require_id_separator(id_separator: str | None) -> str:
        if not id_separator:
            raise ValueError("id_separator must be provided explicitly")
        return id_separator

    @staticmethod
    def _compose_attempted_prefix(
        user_input: dict,
        *,
        id_separator: str,
    ) -> str:
        return id_separator.join(
            (
                user_input.get("name", ""),
                user_input.get("institute", ""),
                user_input.get("sample_ID", ""),
            )
        )
