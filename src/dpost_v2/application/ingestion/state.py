from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
from typing import Any, Mapping

from dpost_v2.application.ingestion.models.candidate import Candidate


@dataclass(frozen=True, slots=True)
class IngestionState:
    """Immutable cross-stage ingestion state snapshot."""

    event: Mapping[str, Any]
    correlation_id: str | None = None
    candidate: Candidate | None = None
    processor: Any | None = None
    record_id: str | None = None
    retry_plan: Mapping[str, Any] | None = None
    sync_warning: str | None = None
    attempt_index: int = 0
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_event(cls, event: Mapping[str, Any]) -> IngestionState:
        """Create the initial state snapshot from one observer event."""
        event_id = str(event.get("event_id", "")).strip()
        if event_id:
            correlation_id = event_id
        else:
            base = f"{event.get('path', '')}|{event.get('observed_at', '')}"
            correlation_id = hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
        return cls(event=dict(event), correlation_id=correlation_id)

    def with_updates(self, **updates: Any) -> IngestionState:
        """Return a new immutable state snapshot with requested field updates."""
        diagnostics_update = updates.pop("diagnostics", None)
        if diagnostics_update is not None:
            merged = dict(self.diagnostics)
            merged.update(dict(diagnostics_update))
            updates["diagnostics"] = merged
        return replace(self, **updates)
