"""Unit coverage for lazy Kadi sync adapter delegation behavior."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from types import ModuleType
from typing import ClassVar

import pytest

from dpost.infrastructure.sync.kadi import KadiSyncAdapter


@dataclass
class _ManagerSpy:
    """Capture delegate construction and sync calls from Kadi adapter."""

    interactions: object
    sync_calls: list[object] = field(default_factory=list)

    instances: ClassVar[list["_ManagerSpy"]] = []

    def sync_record_to_database(self, local_record: object) -> object:
        """Record sync calls and return truthy response for bool coercion."""
        self.sync_calls.append(local_record)
        return {"synced": local_record}


def _install_fake_kadi_manager_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install a fake ``kadi_manager`` module for adapter initialization tests."""
    fake_module = ModuleType("dpost.infrastructure.sync.kadi_manager")
    fake_module.KadiSyncManager = _ManagerSpy
    monkeypatch.setitem(sys.modules, "dpost.infrastructure.sync.kadi_manager", fake_module)


def test_kadi_adapter_requires_interactions_before_first_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise when interactions are missing before first delegate creation."""
    _install_fake_kadi_manager_module(monkeypatch)
    _ManagerSpy.instances = []
    adapter = KadiSyncAdapter()

    with pytest.raises(RuntimeError, match="requires interactions before sync usage"):
        adapter.sync_record_to_database(local_record=object())

    assert _ManagerSpy.instances == []


def test_kadi_adapter_initializes_delegate_once_and_coerces_result_to_bool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create delegate lazily once and forward subsequent sync calls through it."""
    _install_fake_kadi_manager_module(monkeypatch)
    _ManagerSpy.instances = []

    real_init = _ManagerSpy.__init__

    def _tracked_init(self: _ManagerSpy, interactions: object) -> None:
        real_init(self, interactions)
        _ManagerSpy.instances.append(self)

    monkeypatch.setattr(_ManagerSpy, "__init__", _tracked_init)

    adapter = KadiSyncAdapter()
    interactions = object()
    adapter.interactions = interactions
    record_one = object()
    record_two = object()

    first = adapter.sync_record_to_database(local_record=record_one)
    second = adapter.sync_record_to_database(local_record=record_two)

    assert first is True
    assert second is True
    assert len(_ManagerSpy.instances) == 1
    assert _ManagerSpy.instances[0].interactions is interactions
    assert _ManagerSpy.instances[0].sync_calls == [record_one, record_two]
