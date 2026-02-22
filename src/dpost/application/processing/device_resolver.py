"""Resolve device processors by probing ambiguous files."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable

from dpost.application.config import ConfigService, DeviceConfig
from dpost.application.processing.file_processor_abstract import FileProbeResult
from dpost.application.processing.processor_factory import FileProcessorFactory
from dpost.application.retry_delay_policy import RetryDelayPolicy
from dpost.infrastructure.logging import setup_logger

logger = setup_logger(__name__)


class DeviceResolutionKind(str, Enum):
    """Explicit pipeline-facing resolution actions returned by the resolver."""

    ACCEPT = "accept"
    DEFER = "defer"
    REJECT = "reject"


@dataclass(frozen=True)
class ProbeAssessment:
    """Couples a device definition with the result of probing a file."""

    device: DeviceConfig
    result: FileProbeResult
    processor_name: str


@dataclass(frozen=True)
class DeviceResolution:
    """Outcome of attempting to resolve a device for a given path."""

    selected: DeviceConfig | None
    assessments: tuple[ProbeAssessment, ...]
    reason: str
    kind: DeviceResolutionKind
    retry_delay: float | None = None

    def __post_init__(self) -> None:
        if self.kind is DeviceResolutionKind.ACCEPT and self.selected is None:
            raise ValueError("ACCEPT device resolution requires a selected device")
        if self.kind is not DeviceResolutionKind.DEFER and self.retry_delay is not None:
            raise ValueError("retry_delay is only valid for DEFER device resolutions")

    @classmethod
    def accept(
        cls,
        selected: DeviceConfig,
        *,
        assessments: tuple[ProbeAssessment, ...] = tuple(),
        reason: str,
    ) -> "DeviceResolution":
        """Build an explicit accepted-resolution outcome."""
        return cls(
            selected=selected,
            assessments=assessments,
            reason=reason,
            kind=DeviceResolutionKind.ACCEPT,
        )

    @classmethod
    def defer(
        cls,
        *,
        reason: str,
        retry_delay: float | None = None,
        selected: DeviceConfig | None = None,
        assessments: tuple[ProbeAssessment, ...] = tuple(),
    ) -> "DeviceResolution":
        """Build an explicit deferred-resolution outcome."""
        return cls(
            selected=selected,
            assessments=assessments,
            reason=reason,
            kind=DeviceResolutionKind.DEFER,
            retry_delay=retry_delay,
        )

    @classmethod
    def reject(
        cls,
        *,
        reason: str,
        assessments: tuple[ProbeAssessment, ...] = tuple(),
    ) -> "DeviceResolution":
        """Build an explicit rejected-resolution outcome."""
        return cls(
            selected=None,
            assessments=assessments,
            reason=reason,
            kind=DeviceResolutionKind.REJECT,
        )

    @property
    def matched(self) -> bool:
        return self.kind is DeviceResolutionKind.ACCEPT

    @property
    def deferred(self) -> bool:
        """Compatibility helper for callers still checking boolean defer state."""
        return self.kind is DeviceResolutionKind.DEFER


class DeviceResolver:
    """Combine selector rules and processor probes to choose a device."""

    def __init__(
        self, config_service: ConfigService, processor_factory: FileProcessorFactory
    ) -> None:
        self._config_service = config_service
        self._factory = processor_factory

    def resolve(self, path: Path | str) -> DeviceResolution:
        target = Path(path)
        if not target.exists():
            candidates = self._config_service.matching_devices(target)
            selected = self._select_reappear_device(candidates)
            if selected is not None:
                reason = f"Path '{target.name}' missing; waiting for reappearance"
                logger.debug(
                    "DeviceResolver: %s (%s -> %s)", reason, target, selected.identifier
                )
                return DeviceResolution.accept(
                    selected,
                    reason=reason,
                )
            reason = f"Path '{target.name}' disappeared before device resolution"
            logger.debug("DeviceResolver: %s (%s)", reason, target)
            return DeviceResolution.defer(
                reason=reason,
                retry_delay=self._default_retry_delay(),
            )

        deferred_devices = self._config_service.deferred_devices(target)
        candidates: list[DeviceConfig] = self._config_service.matching_devices(target)

        if not candidates and deferred_devices:
            reason = self._defer_reason(deferred_devices, target)
            logger.debug(
                "DeviceResolver: deferring %s (%s)",
                target,
                reason,
            )
            return DeviceResolution.defer(
                reason=reason,
                retry_delay=self._max_retry_delay(deferred_devices),
            )

        if not candidates:
            if target.is_dir() and self._should_defer_empty_directory(target):
                reason = f"Deferred until '{target.name}' gains contents"
                logger.debug("DeviceResolver: deferring %s (%s)", target, reason)
                return DeviceResolution.defer(
                    reason=reason,
                    retry_delay=self._default_retry_delay(),
                )
            reason = "No device selectors matched the file"
            logger.debug("DeviceResolver: %s (%s)", reason, target)
            return DeviceResolution.reject(reason=reason)

        if len(candidates) == 1:
            reason = "Single device matched selectors; probing skipped"
            logger.debug(
                "DeviceResolver: %s (%s -> %s)",
                reason,
                target,
                candidates[0].identifier,
            )
            return DeviceResolution.accept(
                candidates[0],
                reason=reason,
            )

        assessments: list[ProbeAssessment] = [
            self._probe(device, target) for device in candidates
        ]
        selected = self._choose(assessments)
        reason = self._build_reason(selected, assessments, target)

        if selected:
            logger.debug(
                "DeviceResolver: selected '%s' for %s (%s)",
                selected.identifier,
                target,
                reason,
            )
        else:
            logger.debug(
                "DeviceResolver: no processor accepted %s (%s)", target, reason
            )

        if selected is None:
            return DeviceResolution.reject(reason=reason, assessments=tuple(assessments))
        return DeviceResolution.accept(
            selected,
            reason=reason,
            assessments=tuple(assessments),
        )

    @staticmethod
    def _defer_reason(devices: Iterable[DeviceConfig], target: Path) -> str:
        identifiers = ", ".join(device.identifier for device in devices)
        return f"Deferred while '{target.name}' stabilizes (devices: {identifiers})"

    def _max_retry_delay(self, devices: Iterable[DeviceConfig]) -> float:
        delays = [self._device_retry_delay(device) for device in devices]
        return max(delays) if delays else self._default_retry_delay()

    def _device_retry_delay(self, device: DeviceConfig) -> float:
        return RetryDelayPolicy(
            default_delay_seconds=self._default_retry_delay(),
            minimum_delay_seconds=0.0,
        ).coerce(getattr(device.watcher, "retry_delay_seconds", None))

    @staticmethod
    def _default_retry_delay() -> float:
        return 2.0

    @staticmethod
    def _should_defer_empty_directory(path: Path) -> bool:
        try:
            next(path.iterdir())
            return False
        except StopIteration:
            return True
        except FileNotFoundError:
            return True
        except NotADirectoryError:
            return False
        except PermissionError:
            logger.debug(
                "DeviceResolver: lacking permission to inspect %s; deferring", path
            )
            return True
        except OSError as exc:
            logger.debug(
                "DeviceResolver: os error while inspecting %s: %s; deferring", path, exc
            )
            return True

    def _probe(self, device: DeviceConfig, target: Path) -> ProbeAssessment:
        processor = self._factory.get_for_device(device.identifier)
        try:
            result = processor.probe_file(str(target))
        except (
            Exception
        ) as exc:  # pragma: no cover - defensive logging for unexpected probe errors
            logger.warning(
                "DeviceResolver: probe failed for '%s' via %s: %s",
                device.identifier,
                type(processor).__name__,
                exc,
            )
            result = FileProbeResult.unknown(reason=str(exc))
        return ProbeAssessment(
            device=device, result=result, processor_name=type(processor).__name__
        )

    @staticmethod
    def _choose(assessments: Iterable[ProbeAssessment]) -> DeviceConfig | None:
        ordered = list(assessments)
        if not ordered:
            return None

        matches = sorted(
            (item for item in ordered if item.result.is_match()),
            key=lambda item: item.result.confidence,
            reverse=True,
        )

        if matches:
            top = matches[0]
            if len(matches) == 1:
                return top.device
            second = matches[1]
            if top.result.confidence > second.result.confidence:
                return top.device
            # Confidence tie: fall back to selector order for deterministic behaviour.
            first_by_order = next(item for item in ordered if item.result.is_match())
            top_confidence = top.result.confidence
            tied_devices = [
                item.device.identifier
                for item in matches
                if item.result.confidence == top_confidence
            ]
            if len(tied_devices) > 1:
                logger.debug(
                    "DeviceResolver: confidence tie between %s; selecting '%s' by selector order",
                    ", ".join(tied_devices),
                    first_by_order.device.identifier,
                )
            return first_by_order.device

        unknowns = [item for item in ordered if not item.result.is_definitive()]
        if unknowns:
            # Prefer the first processor that stayed inconclusive so the pipeline can inspect it fully.
            return unknowns[0].device

        return None

    @staticmethod
    def _select_reappear_device(
        candidates: Iterable[DeviceConfig],
    ) -> DeviceConfig | None:
        for device in candidates:
            try:
                if float(getattr(device.watcher, "reappear_window_seconds", 0.0)) > 0.0:
                    return device
            except Exception:
                continue
        return None

    @staticmethod
    def _build_reason(
        selected: DeviceConfig | None,
        assessments: Iterable[ProbeAssessment],
        target: Path,
    ) -> str:
        data = list(assessments)
        if not data:
            return "Single device matched selectors"

        if selected is None:
            if all(item.result.is_mismatch() for item in data):
                return "All candidate processors rejected the file during probing"
            return "No definitive probe match"

        assessment = next((item for item in data if item.device == selected), None)
        if assessment and assessment.result.is_match():
            return "Probe match via %s (confidence=%.2f)" % (
                assessment.processor_name,
                assessment.result.confidence,
            )

        return "Fallback to selector order after inconclusive probes"
