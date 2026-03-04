from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import PurePath
from typing import Any, Mapping


_ALLOWED_EVENT_KINDS = frozenset({"created", "modified", "moved", "manual"})


class CandidateError(ValueError):
    """Base candidate-model error."""


class CandidatePathError(CandidateError):
    """Raised when a candidate source path is missing or invalid."""


class CandidateEventTypeError(CandidateError):
    """Raised when an unsupported event kind is provided."""


class CandidateTransitionError(CandidateError):
    """Raised when a candidate enrichment transition is illegal."""


class CandidateSerializationError(CandidateError):
    """Raised when candidate payload serialization fails."""


@dataclass(frozen=True, slots=True)
class Candidate:
    """Immutable ingestion candidate shared across stage boundaries."""

    identity_token: str
    source_path: str
    event_kind: str
    observed_at: float
    size: int | None = None
    modified_at: float | None = None
    fingerprint: str | None = None
    plugin_id: str | None = None
    processor_key: str | None = None
    target_path: str | None = None
    route_tokens: Mapping[str, str] | None = None
    record_id: str | None = None
    persisted_path: str | None = None

    @classmethod
    def from_event(
        cls,
        event: Mapping[str, Any],
        fs_facts: Mapping[str, Any],
    ) -> Candidate:
        """Build a candidate from observer event payload and file facts."""
        raw_path = str(event.get("path", "")).strip()
        if not raw_path:
            raise CandidatePathError("Candidate source path must be non-empty.")

        normalized_path = str(PurePath(raw_path))
        event_kind = str(event.get("event_kind", "")).strip().lower()
        if event_kind not in _ALLOWED_EVENT_KINDS:
            raise CandidateEventTypeError(
                f"Unsupported candidate event kind: '{event_kind}'."
            )

        observed_at = float(event.get("observed_at", 0.0))
        size = fs_facts.get("size")
        modified_at = fs_facts.get("modified_at")
        fingerprint = fs_facts.get("fingerprint")

        identity_payload = {
            "path": normalized_path,
            "event_kind": event_kind,
            "observed_at": observed_at,
            "size": size,
            "modified_at": modified_at,
            "fingerprint": fingerprint,
        }
        identity_token = hashlib.sha256(
            json.dumps(identity_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

        return cls(
            identity_token=identity_token,
            source_path=normalized_path,
            event_kind=event_kind,
            observed_at=observed_at,
            size=int(size) if size is not None else None,
            modified_at=float(modified_at) if modified_at is not None else None,
            fingerprint=str(fingerprint) if fingerprint is not None else None,
        )

    def with_resolution(self, plugin_id: str, processor_key: str) -> Candidate:
        """Return a new candidate with resolve-stage enrichment fields set."""
        if not plugin_id or not processor_key:
            raise CandidateTransitionError(
                "Resolve enrichment requires plugin_id and processor_key."
            )
        return replace(self, plugin_id=plugin_id, processor_key=processor_key)

    def with_route(
        self,
        target_path: str,
        route_tokens: Mapping[str, str],
    ) -> Candidate:
        """Return a new candidate enriched by route-stage output fields."""
        if self.plugin_id is None or self.processor_key is None:
            raise CandidateTransitionError(
                "Route enrichment requires resolution to be present first."
            )
        if not str(target_path).strip():
            raise CandidateTransitionError("Route enrichment requires target_path.")
        normalized_target = str(PurePath(str(target_path))).replace("\\", "/")
        return replace(
            self,
            target_path=normalized_target,
            route_tokens=dict(route_tokens),
        )

    def with_persist_result(self, record_id: str, persisted_path: str) -> Candidate:
        """Return a new candidate enriched by persist-stage output fields."""
        if self.target_path is None:
            raise CandidateTransitionError(
                "Persist enrichment requires a routed target_path first."
            )
        if not record_id:
            raise CandidateTransitionError("Persist enrichment requires record_id.")
        normalized_persisted_path = str(PurePath(str(persisted_path))).replace("\\", "/")
        return replace(
            self,
            record_id=record_id,
            persisted_path=normalized_persisted_path,
        )

    def to_payload(self) -> dict[str, Any]:
        """Serialize the candidate to a JSON-safe diagnostics/event payload."""
        payload = {
            "identity_token": self.identity_token,
            "source_path": self.source_path,
            "event_kind": self.event_kind,
            "observed_at": self.observed_at,
            "size": self.size,
            "modified_at": self.modified_at,
            "fingerprint": self.fingerprint,
            "plugin_id": self.plugin_id,
            "processor_key": self.processor_key,
            "target_path": self.target_path,
            "route_tokens": dict(self.route_tokens or {}),
            "record_id": self.record_id,
            "persisted_path": self.persisted_path,
        }
        try:
            json.dumps(payload, sort_keys=True)
        except TypeError as exc:
            raise CandidateSerializationError(str(exc)) from exc
        return payload
