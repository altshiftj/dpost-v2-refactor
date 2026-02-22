"""Unit coverage for processing routing helper functions."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import Mock

import dpost.application.processing.routing as routing_module


@dataclass(frozen=True)
class _MetadataStub:
    """Minimal device metadata containing record ID reference."""

    record_kadi_id: str | None


@dataclass(frozen=True)
class _DeviceStub:
    """Minimal device config stub exposing metadata."""

    metadata: _MetadataStub


def test_fetch_record_for_prefix_uses_generated_record_identifier(
    monkeypatch,
) -> None:
    """Resolve record using generated record ID when naming policy succeeds."""
    records = Mock()
    existing = object()
    device = _DeviceStub(metadata=_MetadataStub(record_kadi_id="dev-record"))
    filename_pattern = object()
    captured: dict[str, object] = {}
    records.get_record_by_id.return_value = existing

    monkeypatch.setattr(
        routing_module,
        "sanitize_and_validate",
        lambda prefix, **kwargs: captured.__setitem__("sanitize_kwargs", kwargs)
        or ("sanitized", True),
    )
    monkeypatch.setattr(
        routing_module,
        "generate_record_id",
        lambda prefix, dev_kadi_record_id=None, **kwargs: captured.__setitem__(
            "record_kwargs", kwargs
        )
        or f"rid:{prefix}:{dev_kadi_record_id}",
    )

    sanitized, is_valid, record = routing_module.fetch_record_for_prefix(
        records=records,
        filename_prefix="raw",
        device=device,
        filename_pattern=filename_pattern,
        id_separator="__",
    )

    assert sanitized == "sanitized"
    assert is_valid is True
    assert record is existing
    assert captured["sanitize_kwargs"] == {
        "filename_pattern": filename_pattern,
        "id_separator": "__",
    }
    assert captured["record_kwargs"] == {
        "id_separator": "__",
        "current_device": device,
    }
    records.get_record_by_id.assert_called_once_with("rid:sanitized:dev-record")


def test_fetch_record_for_prefix_falls_back_to_lowercase_prefix_when_generation_fails(
    monkeypatch,
) -> None:
    """Fallback to lowercase sanitized prefix when record-id generation raises."""
    records = Mock()
    records.get_record_by_id.return_value = None

    monkeypatch.setattr(
        routing_module,
        "sanitize_and_validate",
        lambda prefix, **_kwargs: ("Sanitized-Prefix", False),
    )

    def _raise(*_args, **_kwargs):
        raise ValueError("missing device context")

    monkeypatch.setattr(routing_module, "generate_record_id", _raise)

    sanitized, is_valid, record = routing_module.fetch_record_for_prefix(
        records=records,
        filename_prefix="raw",
        device=None,
    )

    assert sanitized == "Sanitized-Prefix"
    assert is_valid is False
    assert record is None
    records.get_record_by_id.assert_called_once_with("sanitized-prefix")
