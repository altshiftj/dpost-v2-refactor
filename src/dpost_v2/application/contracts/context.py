"""Runtime and ingestion context contracts for V2 application flows."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping

SUPPORTED_RUNTIME_MODES = frozenset({"headless", "desktop", "shadow", "v1", "v2"})
REQUIRED_DEPENDENCY_IDS = frozenset({"clock", "ui", "sync"})


class ContextValidationError(ValueError):
    """Base exception for context validation failures."""


class UnsupportedRuntimeModeError(ContextValidationError):
    """Raised when runtime mode token is not supported."""


class InvalidCandidateContextError(ContextValidationError):
    """Raised when candidate metadata cannot form a valid processing context."""


class RetryStateError(ContextValidationError):
    """Raised when retry state transitions violate monotonicity constraints."""


def _as_non_empty_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContextValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _validate_path_token(path: str, *, field_name: str) -> str:
    normalized = path.strip()
    if not normalized:
        raise InvalidCandidateContextError(f"{field_name} must be non-empty")
    if "\x00" in normalized:
        raise InvalidCandidateContextError(f"{field_name} contains invalid token")
    return normalized


def _normalize_force_paths(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, tuple | list):
        values = tuple(value)
    else:
        raise InvalidCandidateContextError("force_paths must be a sequence of paths")

    normalized: list[str] = []
    for entry in values:
        if not isinstance(entry, str):
            raise InvalidCandidateContextError("force_paths entries must be strings")
        normalized.append(_validate_path_token(entry, field_name="force_paths entry"))
    return tuple(normalized)


def _freeze_mapping(input_mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(input_mapping))


def _is_profile_allowed_for_mode(
    *,
    mode: str,
    profile: str,
    settings: Mapping[str, object],
) -> bool:
    raw_allowed_profiles = settings.get("allowed_profiles_by_mode")
    if raw_allowed_profiles is None:
        return True
    if not isinstance(raw_allowed_profiles, Mapping):
        raise ContextValidationError("allowed_profiles_by_mode must be a mapping")

    allowed_for_mode = raw_allowed_profiles.get(mode)
    if allowed_for_mode is None:
        return True
    if not isinstance(allowed_for_mode, tuple | list | set):
        raise ContextValidationError(
            "allowed_profiles_by_mode entries must be tuple/list/set"
        )

    allowed_normalized = {
        _as_non_empty_string(entry, field_name="allowed profile").lower()
        for entry in allowed_for_mode
    }
    return profile in allowed_normalized


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    """Immutable runtime-level context shared across processing attempts."""

    mode: str
    profile: str
    session_id: str
    event_id: str
    trace_id: str
    dependency_ids: Mapping[str, str]
    settings_snapshot: Mapping[str, Any]

    def __post_init__(self) -> None:
        mode = self.mode.strip().lower()
        if mode not in SUPPORTED_RUNTIME_MODES:
            raise UnsupportedRuntimeModeError(f"unsupported runtime mode: {self.mode}")
        if self.mode != mode:
            object.__setattr__(self, "mode", mode)

        profile = _as_non_empty_string(self.profile, field_name="profile").lower()
        if self.profile != profile:
            object.__setattr__(self, "profile", profile)

        _as_non_empty_string(self.session_id, field_name="session_id")
        _as_non_empty_string(self.event_id, field_name="event_id")
        _as_non_empty_string(self.trace_id, field_name="trace_id")

        if not isinstance(self.dependency_ids, Mapping):
            raise ContextValidationError("dependency_ids must be a mapping")
        missing_ids = sorted(REQUIRED_DEPENDENCY_IDS - set(self.dependency_ids))
        if missing_ids:
            joined = ", ".join(missing_ids)
            raise ContextValidationError(f"missing dependency_ids: {joined}")
        for key in REQUIRED_DEPENDENCY_IDS:
            _as_non_empty_string(self.dependency_ids.get(key), field_name=f"{key} id")

    @classmethod
    def from_settings(
        cls,
        settings: Mapping[str, object],
        dependency_ids: Mapping[str, str],
    ) -> RuntimeContext:
        """Build and validate runtime context from startup settings and adapters."""
        if not isinstance(settings, Mapping):
            raise ContextValidationError("settings must be a mapping")
        mode = _as_non_empty_string(settings.get("mode"), field_name="mode").lower()
        profile = _as_non_empty_string(
            settings.get("profile"), field_name="profile"
        ).lower()
        if mode not in SUPPORTED_RUNTIME_MODES:
            raise UnsupportedRuntimeModeError(f"unsupported runtime mode: {mode}")
        if not _is_profile_allowed_for_mode(
            mode=mode,
            profile=profile,
            settings=settings,
        ):
            raise UnsupportedRuntimeModeError(
                f"profile '{profile}' is not allowed for mode '{mode}'"
            )

        runtime = cls(
            mode=mode,
            profile=profile,
            session_id=_as_non_empty_string(
                settings.get("session_id"), field_name="session_id"
            ),
            event_id=_as_non_empty_string(
                settings.get("event_id"), field_name="event_id"
            ),
            trace_id=_as_non_empty_string(
                settings.get("trace_id"), field_name="trace_id"
            ),
            dependency_ids=_freeze_mapping(dependency_ids),
            settings_snapshot=_freeze_mapping(settings),
        )
        return validate_runtime_context(runtime)


@dataclass(frozen=True, slots=True)
class ProcessingContext:
    """Immutable per-candidate processing context derived from runtime context."""

    runtime_context: RuntimeContext
    source_path: str
    event_type: str
    observed_at: datetime
    event_id: str
    trace_id: str
    retry_attempt: int = 0
    retry_delay_seconds: float = 0.0
    force_paths: tuple[str, ...] = ()
    failure_reason: str | None = None
    route_hint: str | None = None

    def __post_init__(self) -> None:
        validate_runtime_context(self.runtime_context)
        _validate_path_token(self.source_path, field_name="source_path")
        _as_non_empty_string(self.event_type, field_name="event_type")
        if not isinstance(self.observed_at, datetime):
            raise InvalidCandidateContextError("observed_at must be a datetime")
        _as_non_empty_string(self.event_id, field_name="event_id")
        _as_non_empty_string(self.trace_id, field_name="trace_id")
        if self.retry_attempt < 0:
            raise RetryStateError("retry_attempt cannot be negative")
        if self.retry_delay_seconds < 0:
            raise RetryStateError("retry_delay_seconds cannot be negative")
        _normalize_force_paths(self.force_paths)

    @classmethod
    def for_candidate(
        cls,
        runtime_context: RuntimeContext,
        candidate_event: Mapping[str, object],
    ) -> ProcessingContext:
        """Create processing context for a candidate event."""
        validate_runtime_context(runtime_context)
        if not isinstance(candidate_event, Mapping):
            raise InvalidCandidateContextError("candidate_event must be a mapping")

        source_path = _validate_path_token(
            _as_non_empty_string(
                candidate_event.get("source_path"), field_name="source_path"
            ),
            field_name="source_path",
        )
        event_type = _as_non_empty_string(
            candidate_event.get("event_type"), field_name="event_type"
        )
        observed_at = candidate_event.get("observed_at")
        if not isinstance(observed_at, datetime):
            raise InvalidCandidateContextError("observed_at must be a datetime")

        event_id = candidate_event.get("event_id", runtime_context.event_id)
        trace_id = candidate_event.get("trace_id", runtime_context.trace_id)
        force_paths = _normalize_force_paths(candidate_event.get("force_paths"))

        processing = cls(
            runtime_context=runtime_context,
            source_path=source_path,
            event_type=event_type,
            observed_at=observed_at,
            event_id=_as_non_empty_string(event_id, field_name="event_id"),
            trace_id=_as_non_empty_string(trace_id, field_name="trace_id"),
            force_paths=force_paths,
        )
        return validate_processing_context(processing)

    def with_retry(
        self, *, attempt_index: int, delay_seconds: float
    ) -> ProcessingContext:
        """Clone with updated retry state after validating monotonic constraints."""
        if attempt_index < 0 or attempt_index < self.retry_attempt:
            raise RetryStateError("retry attempt must be monotonic and non-negative")
        if delay_seconds < 0:
            raise RetryStateError("retry delay cannot be negative")
        return replace(
            self,
            retry_attempt=attempt_index,
            retry_delay_seconds=float(delay_seconds),
        )

    def with_failure(self, reason: str) -> ProcessingContext:
        """Clone with normalized failure reason."""
        normalized = _as_non_empty_string(reason, field_name="reason")
        return replace(self, failure_reason=normalized)

    def with_route(self, route_hint: str) -> ProcessingContext:
        """Clone with an explicit route decision hint."""
        normalized = _as_non_empty_string(route_hint, field_name="route_hint")
        return replace(self, route_hint=normalized)


def validate_runtime_context(context: RuntimeContext) -> RuntimeContext:
    """Validate runtime context instance and return it for fluent guard usage."""
    if not isinstance(context, RuntimeContext):
        raise ContextValidationError("expected RuntimeContext instance")
    context.__post_init__()
    return context


def validate_processing_context(context: ProcessingContext) -> ProcessingContext:
    """Validate processing context instance and return it for fluent guard usage."""
    if not isinstance(context, ProcessingContext):
        raise ContextValidationError("expected ProcessingContext instance")
    context.__post_init__()
    return context
