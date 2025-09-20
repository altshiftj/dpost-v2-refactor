"""Resolve device processors by probing ambiguous files."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ipat_watchdog.core.config import ConfigService, DeviceConfig
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import FileProbeResult
from ipat_watchdog.core.processing.processor_factory import FileProcessorFactory

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

    @property
    def matched(self) -> bool:
        return self.selected is not None


class DeviceResolver:
    """Combine selector rules and processor probes to choose a device."""

    def __init__(self, config_service: ConfigService, processor_factory: FileProcessorFactory) -> None:
        self._config_service = config_service
        self._factory = processor_factory

    def resolve(self, path: Path | str) -> DeviceResolution:
        target = Path(path)
        candidates: list[DeviceConfig] = self._config_service.matching_devices(target)

        if not candidates:
            reason = "No device selectors matched the file"
            logger.debug("DeviceResolver: %s (%s)", reason, target)
            return DeviceResolution(selected=None, assessments=tuple(), reason=reason)

        if len(candidates) == 1:
            reason = "Single device matched selectors; probing skipped"
            logger.debug("DeviceResolver: %s (%s -> %s)", reason, target, candidates[0].identifier)
            return DeviceResolution(selected=candidates[0], assessments=tuple(), reason=reason)

        assessments: list[ProbeAssessment] = [self._probe(device, target) for device in candidates]
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
            logger.debug("DeviceResolver: no processor accepted %s (%s)", target, reason)

        return DeviceResolution(selected=selected, assessments=tuple(assessments), reason=reason)

    def _probe(self, device: DeviceConfig, target: Path) -> ProbeAssessment:
        processor = self._factory.get_for_device(device.identifier)
        try:
            result = processor.probe_file(str(target))
        except Exception as exc:  # pragma: no cover - defensive logging for unexpected probe errors
            logger.warning(
                "DeviceResolver: probe failed for '%s' via %s: %s",
                device.identifier,
                type(processor).__name__,
                exc,
            )
            result = FileProbeResult.unknown(reason=str(exc))
        return ProbeAssessment(device=device, result=result, processor_name=type(processor).__name__)

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
            # Tie: honor original order of candidates
            first_by_order = next(item for item in ordered if item.result.is_match())
            return first_by_order.device

        unknowns = [item for item in ordered if not item.result.is_definitive()]
        if unknowns:
            return unknowns[0].device

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
            return (
                "Probe match via %s (confidence=%.2f)"
                % (assessment.processor_name, assessment.result.confidence)
            )

        return "Fallback to selector order after inconclusive probes"

