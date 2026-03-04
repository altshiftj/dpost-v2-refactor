from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.dpost_v2._support.corpus import (
    GoldenCaseSchemaError,
    GoldenCaseSpec,
    load_golden_cases,
)


def test_load_golden_cases_normalizes_order_and_tags(tmp_path: Path) -> None:
    payload = {
        "cases": [
            {
                "case_id": "case-002",
                "filename": "b.txt",
                "candidate": {"source_path": "incoming/b.txt"},
                "expected": {
                    "route": "processed",
                    "record_transition": "created->persisted",
                    "sync_outcome": "queued",
                },
            },
            {
                "case_id": "case-001",
                "filename": "a.txt",
                "candidate": {"source_path": "incoming/a.txt"},
                "expected": {
                    "route": "exceptions",
                    "record_transition": "created->rejected",
                    "sync_outcome": "skipped",
                },
                "tags": ["routing", "golden"],
            },
        ]
    }
    corpus_path = tmp_path / "golden.json"
    corpus_path.write_text(json.dumps(payload), encoding="utf-8")

    cases = load_golden_cases(corpus_path)

    assert [case.case_id for case in cases] == ["case-001", "case-002"]
    assert isinstance(cases[0], GoldenCaseSpec)
    assert cases[0].tags == ("routing", "golden")
    assert cases[1].tags == ()


def test_load_golden_cases_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    payload = {
        "cases": [
            {
                "case_id": "case-001",
                "filename": "a.txt",
                "candidate": {"source_path": "incoming/a.txt"},
                "expected": {
                    "route": "processed",
                    "record_transition": "created->persisted",
                    "sync_outcome": "queued",
                },
            },
            {
                "case_id": "case-001",
                "filename": "b.txt",
                "candidate": {"source_path": "incoming/b.txt"},
                "expected": {
                    "route": "exceptions",
                    "record_transition": "persisted->updated",
                    "sync_outcome": "queued",
                },
            },
        ]
    }
    corpus_path = tmp_path / "golden.json"
    corpus_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(GoldenCaseSchemaError, match="duplicate case_id"):
        load_golden_cases(corpus_path)


def test_load_golden_cases_from_sample_fixture(v2_golden_corpus_path: Path) -> None:
    cases = load_golden_cases(v2_golden_corpus_path)

    assert len(cases) == 3
    assert cases[0].case_id == "case-001"
    assert cases[-1].case_id == "case-003"
