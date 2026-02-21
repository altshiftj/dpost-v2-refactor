"""Domain policy helpers for processing routing decisions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from dpost.domain.processing.models import RoutingDecision

if TYPE_CHECKING:
    from dpost.application.processing.file_processor_abstract import FileProcessorABS
    from dpost.domain.records.local_record import LocalRecord


def determine_routing_decision(
    record: Optional[LocalRecord],
    is_valid_format: bool,
    filename_prefix: str,
    extension: str,
    processor: FileProcessorABS,
) -> RoutingDecision:
    """Determine routing decision based on record state and processor capabilities."""
    if record is None:
        return (
            RoutingDecision.REQUIRE_RENAME
            if not is_valid_format
            else RoutingDecision.ACCEPT
        )

    if not is_valid_format:
        return RoutingDecision.REQUIRE_RENAME

    if processor.is_appendable(record, filename_prefix, extension):
        return RoutingDecision.ACCEPT

    return RoutingDecision.UNAPPENDABLE
