from __future__ import annotations

from pathlib import Path

import pytest

from tests.dpost_v2._support.corpus import GoldenCaseSpec, load_golden_cases
from tests.dpost_v2._support.parity import (
    ParityThresholdError,
    assert_parity_threshold,
    run_parity_report,
)


def test_run_parity_report_detects_deltas(v2_golden_corpus_path: Path) -> None:
    cases = load_golden_cases(v2_golden_corpus_path)

    def v1_runner(case: GoldenCaseSpec) -> dict[str, object]:
        return {
            "route": case.expected["route"],
            "record_transition": case.expected["record_transition"],
            "sync_outcome": case.expected["sync_outcome"],
        }

    def v2_runner(case: GoldenCaseSpec) -> dict[str, object]:
        if case.case_id == "case-002":
            return {
                "route": "exceptions",
                "record_transition": case.expected["record_transition"],
                "sync_outcome": case.expected["sync_outcome"],
            }
        return v1_runner(case)

    report = run_parity_report(cases=cases, v1_runner=v1_runner, v2_runner=v2_runner)

    assert report.total_cases == 3
    assert report.matched_cases == 2
    assert report.mismatched_cases == 1
    assert report.pass_rate == pytest.approx(66.666666, abs=1e-6)
    assert report.results[1].case_id == "case-002"
    assert report.results[1].is_match is False
    assert report.results[1].deltas[0].path == "route"


def test_assert_parity_threshold_raises_with_summary(v2_golden_corpus_path: Path) -> None:
    cases = load_golden_cases(v2_golden_corpus_path)

    def v1_runner(case: GoldenCaseSpec) -> dict[str, object]:
        return {"route": case.expected["route"]}

    def v2_runner(_case: GoldenCaseSpec) -> dict[str, object]:
        return {"route": "exceptions"}

    report = run_parity_report(cases=cases, v1_runner=v1_runner, v2_runner=v2_runner)

    with pytest.raises(ParityThresholdError, match="pass rate"):
        assert_parity_threshold(report, minimum_pass_rate=95.0)
