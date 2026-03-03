# Report: Config Lifecycle Containment Slice

## Date
- 2026-03-03

## Context
- This slice targets strategic item 1 from `docs/planning/archive/20260303-legacy-seams-freshness-rpc.md`.
- Goal: keep production runtime on explicit `ConfigService` injection and contain ambient context helpers to compatibility/testing surfaces.

## Current State
- Ambient config helpers exist in:
  - `src/dpost/application/config/context.py`
  - exports: `init_config`, `set_service`, `get_service`, `reset_service`, `current`, `activate_device`
- Production runtime startup wiring already constructs `ConfigService` directly:
  - `src/dpost/infrastructure/runtime_adapters/startup_dependencies.py`
- Tests and manual flows still use context lifecycle helpers:
  - `tests/integration/test_settings_integration.py`
  - `tests/manual/test_sync_integration.py`

## Target State
- Production paths do not add any new dependence on `dpost.application.config.context`.
- Context helpers remain available only as explicit compatibility/testing seam.
- Ownership is clear in docs and responsibility catalog wording.

## Findings
- Baseline direction is healthy:
  - startup dependency wiring has already moved away from `init_config(...)` usage for production bootstrap.
- Remaining risk is governance drift:
  - without explicit rules, future production modules could reintroduce ambient context lookups.

## Proposed Actions
1. Document seam status:
- mark `config.context` as compatibility/testing-only in architecture docs.
2. Guard production surface:
- add a boundary test or static grep-style check to fail if production startup/runtime modules import `config.context`.
3. Keep tests explicit:
- where tests need ambient lifecycle behavior, import from `config.context` intentionally and locally.

## Risks
- Over-restriction may block legitimate test setup utilities if guard scope is too broad.
- If context API is removed too early, integration/manual characterization tests may lose useful fixtures.

## Validation Plan
- `python -m pytest -q tests/unit/application/config/test_context.py`
- `python -m pytest -q tests/unit/infrastructure/runtime/test_startup_dependencies.py`
- `python -m pytest -q tests/integration`

## References
- `docs/planning/archive/20260303-legacy-seams-freshness-rpc.md`
- `src/dpost/application/config/context.py`
- `src/dpost/infrastructure/runtime_adapters/startup_dependencies.py`

