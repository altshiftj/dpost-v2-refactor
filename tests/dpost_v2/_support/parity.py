"""Parity replay helpers for V2 differential harness tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from tests.dpost_v2._support.corpus import GoldenCaseSpec


class ParityThresholdError(AssertionError):
    """Raised when parity report does not satisfy a required threshold."""


@dataclass(frozen=True, slots=True)
class ParityDelta:
    """One mismatch between V1 and V2 case output payloads."""

    path: str
    v1_value: Any
    v2_value: Any


@dataclass(frozen=True, slots=True)
class ParityCaseResult:
    """Parity outcome for one replay case."""

    case_id: str
    is_match: bool
    deltas: tuple[ParityDelta, ...]


@dataclass(frozen=True, slots=True)
class ParityReport:
    """Aggregate parity results across a deterministic case corpus."""

    total_cases: int
    matched_cases: int
    mismatched_cases: int
    pass_rate: float
    results: tuple[ParityCaseResult, ...]


Runner = Callable[[GoldenCaseSpec], Mapping[str, Any]]


def run_parity_report(
    *,
    cases: Sequence[GoldenCaseSpec],
    v1_runner: Runner,
    v2_runner: Runner,
) -> ParityReport:
    """Replay corpus against both runners and return deterministic parity metrics."""
    results: list[ParityCaseResult] = []
    matched_cases = 0
    for case in cases:
        v1_outcome = dict(v1_runner(case))
        v2_outcome = dict(v2_runner(case))
        deltas = tuple(_diff_values(v1_outcome, v2_outcome, path_prefix=""))
        is_match = len(deltas) == 0
        if is_match:
            matched_cases += 1
        results.append(
            ParityCaseResult(
                case_id=case.case_id,
                is_match=is_match,
                deltas=deltas,
            )
        )

    total_cases = len(results)
    mismatched_cases = total_cases - matched_cases
    pass_rate = 100.0 if total_cases == 0 else (matched_cases / total_cases) * 100.0
    return ParityReport(
        total_cases=total_cases,
        matched_cases=matched_cases,
        mismatched_cases=mismatched_cases,
        pass_rate=pass_rate,
        results=tuple(results),
    )


def assert_parity_threshold(report: ParityReport, *, minimum_pass_rate: float) -> None:
    """Raise a typed assertion error when report pass rate is below threshold."""
    if report.pass_rate >= minimum_pass_rate:
        return
    raise ParityThresholdError(
        "parity pass rate "
        f"{report.pass_rate:.6f}% is below required pass rate {minimum_pass_rate:.6f}% "
        f"({report.mismatched_cases}/{report.total_cases} mismatched)"
    )


def _diff_values(
    v1_value: Any,
    v2_value: Any,
    *,
    path_prefix: str,
) -> list[ParityDelta]:
    if isinstance(v1_value, Mapping) and isinstance(v2_value, Mapping):
        keys = sorted(set(v1_value.keys()) | set(v2_value.keys()))
        deltas: list[ParityDelta] = []
        for key in keys:
            key_path = f"{path_prefix}.{key}" if path_prefix else str(key)
            left = v1_value.get(key, _Missing)
            right = v2_value.get(key, _Missing)
            deltas.extend(_diff_values(left, right, path_prefix=key_path))
        return deltas

    if isinstance(v1_value, list | tuple) and isinstance(v2_value, list | tuple):
        max_length = max(len(v1_value), len(v2_value))
        deltas = []
        for index in range(max_length):
            key_path = f"{path_prefix}[{index}]"
            left = v1_value[index] if index < len(v1_value) else _Missing
            right = v2_value[index] if index < len(v2_value) else _Missing
            deltas.extend(_diff_values(left, right, path_prefix=key_path))
        return deltas

    if v1_value != v2_value:
        return [
            ParityDelta(
                path=path_prefix or "<root>",
                v1_value=None if v1_value is _Missing else v1_value,
                v2_value=None if v2_value is _Missing else v2_value,
            )
        ]
    return []


_Missing = object()
