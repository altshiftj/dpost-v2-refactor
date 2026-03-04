# RPC: V2 CI Gates Alignment (Main vs Rewrite)

## Date
- 2026-03-04

## Status
- Implemented

## Goal
- Keep `main` checks strict and fail-closed for active V2 paths.
- Keep `rewrite/v2` and lane checks lightweight but meaningful as V2 test coverage grows.

## Inputs
- [Lane prompt: ci-v2-gates](../ops/lane-prompts/ci-v2-gates.md)
- [Public CI workflow](../../.github/workflows/public-ci.yml)
- [Rewrite CI workflow](../../.github/workflows/rewrite-ci.yml)
- [Main required checks](../../.github/branch-protection/main.required-checks.json)

## Decisions
1. `Public CI` keeps existing required job names so `main` branch protection contexts remain stable.
2. `Public CI` now validates against the active V2 tree:
- quality checks include `src/dpost_v2` and `tests/dpost_v2` when present,
- unit tests run `tests/dpost_v2`,
- integration tests run explicit V2 integration/smoke targets,
- bootstrap smoke targets point to `tests/dpost_v2` bootstrap tests.
3. `Rewrite CI` remains lightweight for lane branches while adding code-quality and V2 quick-test coverage:
- `rewrite-v2-quality` (ruff/black),
- `rewrite-v2-tests` (`tests/dpost_v2` excluding smoke).
4. `Rewrite CI` runs an additional trunk-only integration subset gate:
- `rewrite-v2-integration` on `rewrite/v2` push/manual dispatch.

## Rationale
- Existing `Public CI` test paths (`tests/unit/dpost_v2`, `tests/integration/dpost_v2`) no longer matched the active layout and could silently skip significant V2 coverage.
- Lane branches need fast checks to prevent merge churn, but trunk still needs an additional integration signal.
- Job-name stability on `main` prevents required-check drift.

## Manual Check
- Confirm `Public CI` contexts in `.github/branch-protection/main.required-checks.json` still match workflow job names.
- Confirm `Rewrite CI` lane runs include:
  - `rewrite-workflow-lint`
  - `rewrite-artifact-hygiene`
  - `rewrite-v2-quality`
  - `rewrite-v2-tests`
- Confirm `rewrite/v2` push runs additionally include `rewrite-v2-integration`.

