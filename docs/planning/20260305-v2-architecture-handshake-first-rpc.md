# 20260305 V2 Architecture Handshake-First RPC

## Goal
- Fully wire V2 architecture boundaries so runtime surfaces handshake correctly end-to-end before migrating deeper device functionality.

## Success Criteria
- Entrypoint -> startup -> dependencies -> composition -> runtime loop executes without fallback shims.
- Port bindings are concrete adapter objects (not dict placeholders) at runtime.
- Plugin host activation is profile-aware and PC-scoped device policy is enforceable.
- Ingestion pipeline consumes processor contracts through explicit handshake points.
- PC plugin payload shaping and sync backend transport remain separated.

## Non-Goals
- Device-specific behavioral parity migration for `sem_phenomxl2`, `psa_horiba`, `utm_zwick`.
- Continuous watch-loop behavior hardening beyond deterministic single-pass validation.
- Legacy runtime mode reintroduction.

## Phase Plan

### Phase A: Handshake Contract Baseline
- Lock current runtime ceiling and failure boundaries with tests and report evidence.
- Define handshake matrix (caller, callee, payload, invariant, failure mode) across layers.

### Phase B: Startup/Dependency Handshake
- Ensure settings service produces complete startup payload and provenance.
- Ensure dependency resolver returns concrete factories for plugin host, filesystem/file ops, record store, sync, UI/event/clock.
- Remove hidden fallback reliance from startup wiring path.

### Phase C: Composition/Port Handshake
- Enforce strict port protocol conformance in composition.
- Verify composed app receives typed bindings and stable diagnostics.
- Fail fast when bindings degrade to fallback-only path.

### Phase D: Plugin Handshake (Policy First)
- Wire plugin discovery + host activation in startup/composition.
- Encode PC plugin as workstation policy owner and limit selected device plugins by PC scope.
- Keep device plugin ownership to processing behavior only.

### Phase E: Ingestion Handshake
- Ensure resolve stage selects processor and transform step executes processor contract (`prepare/can_process/process`) deterministically.
- Ensure downstream route/persist/post-persist consume processor output via typed state handoff.

### Phase F: Sync Handshake Separation
- Ensure PC plugin shapes payload and sync backend performs transport only.
- Ensure sync failures emit canonical events and do not mutate policy ownership boundaries.

### Phase G: End-to-End Handshake Smoke
- Headless run over real files in temp workspace verifies:
  - deterministic event discovery,
  - concrete plugin resolution (no `default_device` fallback),
  - concrete file side effects,
  - stable runtime terminal reasons.

## TDD Sequence
1. Add failing tests for one handshake seam.
2. Implement minimal wiring to pass.
3. Refactor without crossing layer boundaries.
4. Capture diagnostics/report evidence.
5. Repeat for next seam.

## Validation Gates
- `python -m ruff check src/dpost_v2 tests/dpost_v2`
- `python -m pytest -q tests/dpost_v2/test___main__.py`
- `python -m pytest -q tests/dpost_v2/runtime tests/dpost_v2/application/startup tests/dpost_v2/application/runtime`
- `python -m pytest -q tests/dpost_v2/application/ingestion tests/dpost_v2/plugins`
- `python -m pytest -q tests/dpost_v2`

## Risks and Mitigations
- Risk: Regressions hidden by permissive fallback adapters.
  - Mitigation: Add explicit tests that assert concrete binding types and plugin ids.
- Risk: PC/device/sync responsibilities blur during wiring.
  - Mitigation: Add seam tests for ownership boundaries and contract payload shape.
- Risk: Runtime appears successful without real side effects.
  - Mitigation: Include filesystem assertions in smoke tests and report those as hard gates.

## Deliverables
- Handshake-first checklist in `docs/checklists/`.
- Runtime ceiling and progress reports in `docs/reports/`.
- Green targeted test slices per phase.
