"""Notification helpers for success paths in the processing workflow."""
from __future__ import annotations

from pathlib import Path

from ipat_watchdog.core.interactions import InfoMessages, UserInteractionPort


def notify_success(interactions: UserInteractionPort, src_path: str, final_path: str) -> None:
    item_type = "Folder" if Path(src_path).is_dir() else "File"
    interactions.show_info(
        InfoMessages.SUCCESS,
        InfoMessages.ITEM_RENAMED.format(item_type=item_type, filename=Path(final_path).name),
    )
