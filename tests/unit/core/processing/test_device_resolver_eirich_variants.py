from __future__ import annotations

from pathlib import Path

from ipat_watchdog.core.config import ConfigService, DeviceConfig, PCConfig
from ipat_watchdog.core.processing.device_resolver import DeviceResolver
from ipat_watchdog.device_plugins.mix_eirich.file_processor import FileProcessorEirich
from ipat_watchdog.device_plugins.mix_eirich.settings import build_config


class _StubProcessorFactory:
    def __init__(self, configs_by_id: dict[str, DeviceConfig]) -> None:
        self._configs_by_id = configs_by_id

    def get_for_device(self, device_id: str) -> FileProcessorEirich:
        config = self._configs_by_id[device_id]
        return FileProcessorEirich(config)


def _build_resolver() -> tuple[DeviceResolver, DeviceConfig, DeviceConfig]:
    config_el1 = build_config("EL1")
    config_r01 = build_config("R01")
    service = ConfigService(PCConfig(identifier="eirich_test_pc"), [config_el1, config_r01])
    factory = _StubProcessorFactory(
        {
            config_el1.identifier: config_el1,
            config_r01.identifier: config_r01,
        }
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
