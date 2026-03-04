"""Processing status/reason/outcome domain models for V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class ProcessingModelError(ValueError):
    """Base class for processing domain model errors."""


class ProcessingStatusError(ProcessingModelError):
    """Raised when status token cannot be resolved to domain enum."""


class ProcessingOutcomeConsistencyError(ProcessingModelError):
    """Raised when status/reason combination is illegal."""


class ProcessingOutcomeMetadataError(ProcessingModelError):
    """Raised when required status-specific metadata is missing or invalid."""


class ProcessingReasonNamespaceError(ProcessingModelError):
    """Raised when reason namespace is not recognized."""


class ProcessingStatus(str, Enum):
    """Processing outcome status categories."""

    SUCCESS = "success"
    REJECTED = "rejected"
    FAILED = "failed"
    RETRY = "retry"


ALLOWED_REASON_NAMESPACES = frozenset(
    {
        "success",
        "validation",
        "failure",
        "retry",
        "processing",
        "error",
    },
)


@dataclass(frozen=True)
class ProcessingReason:
    """Machine-readable reason namespace/code pair."""

    namespace: str
    code: str

    def __post_init__(self) -> None:
        if self.namespace not in ALLOWED_REASON_NAMESPACES:
            raise ProcessingReasonNamespaceError(
                f"Unknown reason namespace '{self.namespace}'.",
            )
        if not self.code:
            raise ProcessingOutcomeConsistencyError(
                "Reason code must be non-empty.",
            )

    @property
    def token(self) -> str:
        """Return stable wire-format reason token."""
        return f"{self.namespace}.{self.code}"


@dataclass(frozen=True)
class ProcessingOutcome:
    """Immutable processing outcome consumed across V2 layers."""

    candidate_id: str
    status: ProcessingStatus
    reason: ProcessingReason
    retry_delay_seconds: float | None = None
    retry_attempt: int | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ProcessingOutcomeMetadataError("candidate_id must be non-empty.")

        if self.status is ProcessingStatus.RETRY:
            if self.retry_delay_seconds is None or self.retry_attempt is None:
                raise ProcessingOutcomeMetadataError(
                    "Retry outcomes require retry_delay_seconds and retry_attempt.",
                )
            if self.retry_delay_seconds < 0:
                raise ProcessingOutcomeMetadataError(
                    "retry_delay_seconds must be >= 0 for retry outcomes.",
                )
            if self.retry_attempt < 0:
                raise ProcessingOutcomeMetadataError(
                    "retry_attempt must be >= 0 for retry outcomes.",
                )
        elif self.retry_delay_seconds is not None or self.retry_attempt is not None:
            raise ProcessingOutcomeMetadataError(
                "Non-retry outcomes must not include retry metadata.",
            )

        if self.status is ProcessingStatus.SUCCESS and self.reason.namespace in {
            "failure",
            "error",
            "retry",
        }:
            raise ProcessingOutcomeConsistencyError(
                "Success outcome cannot use failure/error/retry reason namespace.",
            )

    def to_dict(self) -> dict[str, object]:
        """Serialize outcome with stable field names for cross-layer contracts."""
        return {
            "candidate_id": self.candidate_id,
            "status": self.status.value,
            "reason_namespace": self.reason.namespace,
            "reason_code": self.reason.code,
            "retry_delay_seconds": self.retry_delay_seconds,
            "retry_attempt": self.retry_attempt,
            "metadata": dict(self.metadata),
        }


def _coerce_status(status_token: str) -> ProcessingStatus:
    try:
        return ProcessingStatus(status_token)
    except ValueError as exc:
        raise ProcessingStatusError(f"Unknown processing status '{status_token}'.") from exc


def success_outcome(
    *,
    candidate_id: str,
    reason_code: str,
    metadata: Mapping[str, str] | None = None,
) -> ProcessingOutcome:
    """Build valid success outcome."""
    return ProcessingOutcome(
        candidate_id=candidate_id,
        status=ProcessingStatus.SUCCESS,
        reason=ProcessingReason(namespace="success", code=reason_code),
        metadata=dict(metadata or {}),
    )


def rejected_outcome(
    *,
    candidate_id: str,
    reason_code: str,
    metadata: Mapping[str, str] | None = None,
) -> ProcessingOutcome:
    """Build valid rejected outcome."""
    return ProcessingOutcome(
        candidate_id=candidate_id,
        status=ProcessingStatus.REJECTED,
        reason=ProcessingReason(namespace="validation", code=reason_code),
        metadata=dict(metadata or {}),
    )


def failed_outcome(
    *,
    candidate_id: str,
    reason_code: str,
    metadata: Mapping[str, str] | None = None,
) -> ProcessingOutcome:
    """Build valid failed outcome."""
    return ProcessingOutcome(
        candidate_id=candidate_id,
        status=ProcessingStatus.FAILED,
        reason=ProcessingReason(namespace="failure", code=reason_code),
        metadata=dict(metadata or {}),
    )


def retry_outcome(
    *,
    candidate_id: str,
    reason_code: str,
    retry_delay_seconds: float,
    retry_attempt: int,
    metadata: Mapping[str, str] | None = None,
) -> ProcessingOutcome:
    """Build valid retry outcome with retry metadata."""
    return ProcessingOutcome(
        candidate_id=candidate_id,
        status=ProcessingStatus.RETRY,
        reason=ProcessingReason(namespace="retry", code=reason_code),
        retry_delay_seconds=retry_delay_seconds,
        retry_attempt=retry_attempt,
        metadata=dict(metadata or {}),
    )


def outcome_from_dict(payload: Mapping[str, object]) -> ProcessingOutcome:
    """Deserialize processing outcome from stable wire dict fields."""
    status = _coerce_status(str(payload["status"]))
    return ProcessingOutcome(
        candidate_id=str(payload["candidate_id"]),
        status=status,
        reason=ProcessingReason(
            namespace=str(payload["reason_namespace"]),
            code=str(payload["reason_code"]),
        ),
        retry_delay_seconds=(
            float(payload["retry_delay_seconds"])
            if payload.get("retry_delay_seconds") is not None
            else None
        ),
        retry_attempt=(
            int(payload["retry_attempt"])
            if payload.get("retry_attempt") is not None
            else None
        ),
        metadata={str(k): str(v) for k, v in dict(payload.get("metadata", {})).items()},
    )


def outcome_from_classification(
    *,
    candidate_id: str,
    status_token: str,
    reason_token: str,
    retry_delay_seconds: float | None = None,
    retry_attempt: int | None = None,
    metadata: Mapping[str, str] | None = None,
) -> ProcessingOutcome:
    """Convert policy-level status/reason tokens to domain outcome model."""
    status = _coerce_status(status_token)
    if "." not in reason_token:
        raise ProcessingOutcomeConsistencyError(
            "reason_token must contain namespace and code separated by '.'.",
        )
    namespace, code = reason_token.split(".", 1)
    return ProcessingOutcome(
        candidate_id=candidate_id,
        status=status,
        reason=ProcessingReason(namespace=namespace, code=code),
        retry_delay_seconds=retry_delay_seconds,
        retry_attempt=retry_attempt,
        metadata=dict(metadata or {}),
    )

