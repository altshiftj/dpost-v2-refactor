"""Resolve device processors by probing ambiguous files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from dpost.application.config import ConfigService, DeviceConfig
from dpost.application.processing.file_processor_abstract import FileProbeResult
from dpost.application.processing.processor_factory import FileProcessorFactory
from dpost.infrastructure.logging import setup_logger

logger = setup_logger(__name__)


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
    deferred: bool = False
    retry_delay: float | None = None

    @property
    def matched(self) -> bool:
        return self.selected is not None


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
                return DeviceResolution(
                    selected=selected,
                    assessments=tuple(),
                    reason=reason,
                )
            reason = f"Path '{target.name}' disappeared before device resolution"
            logger.debug("DeviceResolver: %s (%s)", reason, target)
            return DeviceResolution(
                selected=None,
                assessments=tuple(),
                reason=reason,
                deferred=True,
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
            return DeviceResolution(
                selected=None,
                assessments=tuple(),
                reason=reason,
                deferred=True,
                retry_delay=self._max_retry_delay(deferred_devices),
            )

        if not candidates:
            if target.is_dir() and self._should_defer_empty_directory(target):
                reason = f"Deferred until '{target.name}' gains contents"
                logger.debug("DeviceResolver: deferring %s (%s)", target, reason)
                return DeviceResolution(
                    selected=None,
                    assessments=tuple(),
                    reason=reason,
                    deferred=True,
                    retry_delay=self._default_retry_delay(),
                )
            reason = "No device selectors matched the file"
            logger.debug("DeviceResolver: %s (%s)", reason, target)
            return DeviceResolution(selected=None, assessments=tuple(), reason=reason)

        if len(candidates) == 1:
            reason = "Single device matched selectors; probing skipped"
            logger.debug(
                "DeviceResolver: %s (%s -> %s)",
                reason,
                target,
                candidates[0].identifier,
            )
            return DeviceResolution(
                selected=candidates[0], assessments=tuple(), reason=reason
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

        return DeviceResolution(
            selected=selected, assessments=tuple(assessments), reason=reason
        )

    @staticmethod
    def _defer_reason(devices: Iterable[DeviceConfig], target: Path) -> str:
        identifiers = ", ".join(device.identifier for device in devices)
        return f"Deferred while '{target.name}' stabilizes (devices: {identifiers})"

    def _max_retry_delay(self, devices: Iterable[DeviceConfig]) -> float:
        delays = [self._device_retry_delay(device) for device in devices]
        return max(delays) if delays else self._default_retry_delay()

    def _device_retry_delay(self, device: DeviceConfig) -> float:
        try:
            return float(device.watcher.retry_delay_seconds)
        except Exception:
            return self._default_retry_delay()

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
