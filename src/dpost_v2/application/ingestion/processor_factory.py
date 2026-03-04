from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable


class ProcessorFactoryError(RuntimeError):
    """Base processor-factory selection error."""


class ProcessorNotFoundError(ProcessorFactoryError):
    """Raised when no processors match a candidate/profile request."""


class ProcessorAmbiguousMatchError(ProcessorFactoryError):
    """Raised when top-ranked processor candidates are ambiguous."""


class ProcessorInitializationError(ProcessorFactoryError):
    """Raised when a selected processor fails construction."""


class InvalidProcessorError(ProcessorFactoryError):
    """Raised when constructed processor violates required contract surface."""


@dataclass(frozen=True, slots=True)
class SelectionDescriptor:
    """Metadata describing processor selection decisions."""

    plugin_id: str
    processor_key: str
    capability_reason: str
    cache_hit: bool


@dataclass(frozen=True, slots=True)
class ProcessorSelection:
    """Selected processor instance paired with selection metadata."""

    processor: Any
    descriptor: SelectionDescriptor


class ProcessorFactory:
    """Deterministic processor selector over plugin-catalog candidates."""

    def __init__(
        self,
        *,
        catalog_lookup: Callable[[Any, str | None], Iterable[Any]],
        cache_enabled: bool = True,
    ) -> None:
        """Initialize processor factory with lookup callable and cache settings."""
        self._catalog_lookup = catalog_lookup
        self._cache_enabled = cache_enabled
        self._cache: dict[tuple[str, str | None], Any] = {}

    def select(self, *, candidate: Any, profile: str | None) -> ProcessorSelection:
        """Select and build one processor for a candidate/profile combination."""
        matches = list(self._catalog_lookup(candidate, profile))
        if not matches:
            raise ProcessorNotFoundError("No compatible processor candidates were found.")

        ranked = sorted(
            matches,
            key=lambda item: (-int(getattr(item, "score", 0)), str(getattr(item, "plugin_id", ""))),
        )
        top = ranked[0]
        top_score = int(getattr(top, "score", 0))
        top_id = str(getattr(top, "plugin_id", ""))
        duplicate_top = [
            item
            for item in ranked
            if int(getattr(item, "score", 0)) == top_score
            and str(getattr(item, "plugin_id", "")) == top_id
        ]
        if len(duplicate_top) > 1:
            raise ProcessorAmbiguousMatchError(
                "Multiple equally-ranked processor candidates share the same plugin id."
            )

        cache_key = (top_id, profile)
        if self._cache_enabled and cache_key in self._cache:
            cached = self._cache[cache_key]
            return ProcessorSelection(
                processor=cached,
                descriptor=SelectionDescriptor(
                    plugin_id=top_id,
                    processor_key=top_id,
                    capability_reason="cache_hit",
                    cache_hit=True,
                ),
            )

        try:
            processor = top.build()
        except Exception as exc:  # noqa: BLE001
            raise ProcessorInitializationError(str(exc)) from exc

        if not hasattr(processor, "process") or not callable(getattr(processor, "process")):
            raise InvalidProcessorError(
                "Constructed processor must define a callable 'process' method."
            )

        if self._cache_enabled:
            self._cache[cache_key] = processor

        return ProcessorSelection(
            processor=processor,
            descriptor=SelectionDescriptor(
                plugin_id=top_id,
                processor_key=top_id,
                capability_reason="ranked_match",
                cache_hit=False,
            ),
        )
