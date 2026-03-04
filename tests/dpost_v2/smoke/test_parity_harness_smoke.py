from __future__ import annotations

from pathlib import Path

from tests.dpost_v2._support.corpus import GoldenCaseSpec, load_golden_cases
from tests.dpost_v2._support.parity import assert_parity_threshold, run_parity_report


def test_parity_smoke_passes_on_identical_runner_outputs(
    v2_golden_corpus_path: Path,
) -> None:
    cases = load_golden_cases(v2_golden_corpus_path)

    def runner(case: GoldenCaseSpec) -> dict[str, object]:
        return {
            "route": case.expected["route"],
            "record_transition": case.expected["record_transition"],
            "sync_outcome": case.expected["sync_outcome"],
        }

    report = run_parity_report(cases=cases, v1_runner=runner, v2_runner=runner)
    assert_parity_threshold(report, minimum_pass_rate=100.0)

    assert report.total_cases == 3
    assert report.mismatched_cases == 0
