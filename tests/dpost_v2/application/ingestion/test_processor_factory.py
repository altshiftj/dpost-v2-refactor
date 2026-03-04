from __future__ import annotations

import pytest

from dpost_v2.application.ingestion.processor_factory import (
    ProcessorAmbiguousMatchError,
    ProcessorFactory,
    ProcessorNotFoundError,
)


class _Plugin:
    def __init__(self, plugin_id: str, score: int) -> None:
        self.plugin_id = plugin_id
        self.score = score

    def build(self):
        return type("Proc", (), {"process": lambda self: None})()


def test_processor_factory_selects_highest_rank_deterministically() -> None:
    factory = ProcessorFactory(
        catalog_lookup=lambda candidate, profile: [
            _Plugin("b", 10),
            _Plugin("a", 10),
            _Plugin("c", 9),
        ]
    )

    selected = factory.select(candidate={"kind": "x"}, profile="p")

    assert selected.descriptor.plugin_id == "a"


def test_processor_factory_raises_for_no_matches() -> None:
    factory = ProcessorFactory(catalog_lookup=lambda candidate, profile: [])

    with pytest.raises(ProcessorNotFoundError):
        factory.select(candidate={"kind": "x"}, profile="p")


def test_processor_factory_raises_for_ambiguous_top_match() -> None:
    factory = ProcessorFactory(
        catalog_lookup=lambda candidate, profile: [_Plugin("a", 10), _Plugin("a", 10)]
    )

    with pytest.raises(ProcessorAmbiguousMatchError):
        factory.select(candidate={"kind": "x"}, profile="p")


def test_processor_factory_reuses_cache() -> None:
    plugin = _Plugin("a", 10)
    factory = ProcessorFactory(catalog_lookup=lambda candidate, profile: [plugin])

    left = factory.select(candidate={"kind": "x"}, profile="p")
    right = factory.select(candidate={"kind": "x"}, profile="p")

    assert left.processor is right.processor
    assert right.descriptor.cache_hit is True
