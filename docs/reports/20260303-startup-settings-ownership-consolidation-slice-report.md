# Report: Startup Settings Ownership Consolidation Slice

## Date
- 2026-03-03

## Context
- This slice targets strategic item 3 from `docs/planning/20260303-legacy-seams-freshness-rpc.md`.
- Goal: establish one obvious owner for startup settings parsing/validation policy.

## Current State
- Startup composition orchestrator:
  - `src/dpost/runtime/composition.py`
- Bootstrap settings collection and defaults:
  - `src/dpost/runtime/bootstrap.py`
- Override-aware startup settings resolver:
  - `src/dpost/runtime/startup_config.py`
- Settings logic is improved but split across two policy surfaces (`bootstrap` and `startup_config`).

## Target State
- Clear single-owner boundary for startup settings parsing/validation.
- `composition.py` remains orchestration-only.
- `bootstrap.py` stays focused on runtime assembly using resolved settings objects.

## Findings
- Existing implementation is stable and explicit enough for current behavior.
- Contributor ambiguity remains:
  - where to add/change env parse rules,
  - which module owns port coercion and override precedence.

## Proposed Actions
1. Choose one policy owner:
- either keep ownership in `startup_config.py` and shrink policy code in `bootstrap.py`,
- or reverse, but avoid dual ownership.
2. Keep contracts shared:
- `StartupSettings` contract remains the shared type boundary.
3. Add focused tests for precedence:
- explicit argument > `DPOST_*` env > base `PC_NAME`/`DEVICE_PLUGINS` fallback behavior.

## Risks
- Touching startup settings can accidentally alter operator startup behavior.
- Duplication removal can break subtle fallback ordering if tests are incomplete.

## Validation Plan
- `python -m pytest -q tests/unit/runtime/test_startup_config.py`
- `python -m pytest -q tests/unit/runtime/test_bootstrap.py tests/unit/runtime/test_bootstrap_additional.py`
- `python -m pytest -q tests/unit/runtime/test_composition.py`

## References
- `docs/planning/20260303-legacy-seams-freshness-rpc.md`
- `src/dpost/runtime/composition.py`
- `src/dpost/runtime/bootstrap.py`
- `src/dpost/runtime/startup_config.py`
