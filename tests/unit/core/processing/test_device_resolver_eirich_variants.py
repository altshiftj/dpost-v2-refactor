from __future__ import annotations

from pathlib import Path
import logging

from ipat_watchdog.core.config import ConfigService, DeviceConfig, PCConfig
from ipat_watchdog.core.processing.device_resolver import DeviceResolver
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProcessorABS,
    FileProbeResult,
    ProcessingOutput,
)
from ipat_watchdog.device_plugins.rmx_eirich_el1.file_processor import (
    FileProcessorEirich as FileProcessorEirichEL1,
)
from ipat_watchdog.device_plugins.rmx_eirich_r01.file_processor import (
    FileProcessorEirich as FileProcessorEirichR01,
)
from ipat_watchdog.device_plugins.rmx_eirich_el1.settings import (
    build_config as build_el1_config,
)
from ipat_watchdog.device_plugins.rmx_eirich_r01.settings import (
    build_config as build_r01_config,
)


class _StubProcessorFactory:
    def __init__(
        self,
        configs_by_id: dict[str, DeviceConfig],
        processors_by_id: dict[str, type[FileProcessorABS]],
    ) -> None:
        self._configs_by_id = configs_by_id
        self._processors_by_id = processors_by_id

    def get_for_device(self, device_id: str) -> FileProcessorABS:
        config = self._configs_by_id[device_id]
        processor_cls = self._processors_by_id[device_id]
        return processor_cls(config)


def _build_resolver() -> tuple[DeviceResolver, DeviceConfig, DeviceConfig]:
    config_el1 = build_el1_config()
    config_r01 = build_r01_config()
    service = ConfigService(PCConfig(identifier="eirich_test_pc"), [config_el1, config_r01])
    factory = _StubProcessorFactory(
        {
            config_el1.identifier: config_el1,
            config_r01.identifier: config_r01,
        },
        {
            config_el1.identifier: FileProcessorEirichEL1,
            config_r01.identifier: FileProcessorEirichR01,
        },
    )
    return DeviceResolver(service, factory), config_el1, config_r01


def test_device_resolver_selects_el1_by_filename(tmp_path: Path) -> None:
    resolver, config_el1, _ = _build_resolver()
    target = tmp_path / "Eirich_EL1_TrendFile_20250924_095653.txt"
    target.write_text("payload", encoding="utf-8")

    resolution = resolver.resolve(target)

    assert resolution.selected == config_el1


def test_device_resolver_selects_r01_by_filename(tmp_path: Path) -> None:
    resolver, _, config_r01 = _build_resolver()
    target = tmp_path / "Eirich_R01_TrendFile_20250731_103330.txt"
    target.write_text("payload", encoding="utf-8")

    resolution = resolver.resolve(target)

    assert resolution.selected == config_r01


def test_device_resolver_logs_confidence_tie(tmp_path: Path, caplog) -> None:
    config_el1 = build_el1_config()
    config_r01 = build_r01_config()
    service = ConfigService(PCConfig(identifier="eirich_test_pc"), [config_el1, config_r01])

    class _TieProbeProcessor(FileProcessorABS):
        def device_specific_processing(
            self,
            src_path: str,
            record_path: str,
            file_id: str,
            extension: str,
        ) -> ProcessingOutput:
            return ProcessingOutput(final_path=src_path, datatype="stub")

        def probe_file(self, filepath: str) -> FileProbeResult:
            return FileProbeResult.match(confidence=0.9, reason="tie")

    factory = _StubProcessorFactory(
        {
            config_el1.identifier: config_el1,
            config_r01.identifier: config_r01,
        },
        {
            config_el1.identifier: _TieProbeProcessor,
            config_r01.identifier: _TieProbeProcessor,
        },
    )
    resolver = DeviceResolver(service, factory)
    target = tmp_path / "Eirich_EL1_TrendFile_20250924_095653.txt"
    target.write_text("payload", encoding="utf-8")

    caplog.set_level(logging.DEBUG, logger="ipat_watchdog.core.processing.device_resolver")
    resolution = resolver.resolve(target)

    assert resolution.selected == config_el1
    assert any("confidence tie" in record.message for record in caplog.records)
