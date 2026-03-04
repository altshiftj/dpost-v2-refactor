"""Golden corpus models and loaders for V2 behavior-capture harnesses."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


class GoldenCaseSchemaError(ValueError):
    """Raised when the golden corpus structure is malformed."""


@dataclass(frozen=True, slots=True)
class GoldenCaseSpec:
    """One deterministic behavior-capture case for parity replay."""

    case_id: str
    filename: str
    candidate: Mapping[str, Any]
    expected: Mapping[str, Any]
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        case_id = self.case_id.strip()
        if not case_id:
            raise GoldenCaseSchemaError("case_id must be a non-empty string")
        filename = self.filename.strip()
        if not filename:
            raise GoldenCaseSchemaError("filename must be a non-empty string")
        if not isinstance(self.candidate, Mapping):
            raise GoldenCaseSchemaError("candidate must be a mapping")
        if not isinstance(self.expected, Mapping):
            raise GoldenCaseSchemaError("expected must be a mapping")

        for key in ("route", "record_transition", "sync_outcome"):
            if key not in self.expected:
                raise GoldenCaseSchemaError(
                    f"expected must include required key {key!r}"
                )

        object.__setattr__(self, "case_id", case_id)
        object.__setattr__(self, "filename", filename)
        object.__setattr__(self, "candidate", MappingProxyType(dict(self.candidate)))
        object.__setattr__(self, "expected", MappingProxyType(dict(self.expected)))
        object.__setattr__(self, "tags", tuple(self.tags))


def load_golden_cases(corpus_path: Path | str) -> tuple[GoldenCaseSpec, ...]:
    """Load and validate golden corpus cases from a JSON file."""
    path = Path(corpus_path)
    payload = _load_json_payload(path)
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list):
        raise GoldenCaseSchemaError("corpus payload must contain list field 'cases'")

    case_specs = tuple(_normalize_case(raw_case) for raw_case in raw_cases)
    _ensure_unique_case_ids(case_specs)
    return tuple(sorted(case_specs, key=lambda case: case.case_id))


def _load_json_payload(path: Path) -> Mapping[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GoldenCaseSchemaError(f"invalid JSON in corpus file: {path}") from exc
    if not isinstance(raw, Mapping):
        raise GoldenCaseSchemaError("corpus payload must be a JSON object")
    return raw


def _normalize_case(raw_case: object) -> GoldenCaseSpec:
    if not isinstance(raw_case, Mapping):
        raise GoldenCaseSchemaError("each corpus case must be a JSON object")
    raw_tags = raw_case.get("tags", ())
    if not isinstance(raw_tags, list | tuple):
        raise GoldenCaseSchemaError("case tags must be a list/tuple of strings")
    tags = tuple(_normalize_tag(value) for value in raw_tags)
    return GoldenCaseSpec(
        case_id=_require_non_empty_string(raw_case.get("case_id"), key="case_id"),
        filename=_require_non_empty_string(raw_case.get("filename"), key="filename"),
        candidate=_require_mapping(raw_case.get("candidate"), key="candidate"),
        expected=_require_mapping(raw_case.get("expected"), key="expected"),
        tags=tags,
    )


def _normalize_tag(value: object) -> str:
    if not isinstance(value, str):
        raise GoldenCaseSchemaError("case tags must contain only strings")
    tag = value.strip()
    if not tag:
        raise GoldenCaseSchemaError("case tags must be non-empty strings")
    return tag


def _require_non_empty_string(value: object, *, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GoldenCaseSchemaError(f"{key} must be a non-empty string")
    return value.strip()


def _require_mapping(value: object, *, key: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GoldenCaseSchemaError(f"{key} must be a mapping")
    return dict(value)


def _ensure_unique_case_ids(cases: tuple[GoldenCaseSpec, ...]) -> None:
    seen: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            raise GoldenCaseSchemaError(f"duplicate case_id: {case.case_id}")
        seen.add(case.case_id)
