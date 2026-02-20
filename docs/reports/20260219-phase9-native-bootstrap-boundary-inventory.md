# Phase 9 Native dpost Bootstrap Boundary Inventory

## Date
- 2026-02-19

## Context
- Phase 8 cutover/release gate tasks are prepared.
- Forward migration planning now targets full strangler completion beyond
  transition wrappers.
- Phase 9 starts with a tests-first contract for native `dpost` bootstrap
  boundaries before implementation.

## Inventory Scope
- Canonical runtime startup/composition boundary modules:
  - `src/dpost/runtime/bootstrap.py`
  - `src/dpost/runtime/composition.py`
- Existing migration identity contract:
  - `tests/migration/test_phase8_cutover_identity.py`

## Findings
| Area | Observation | Evidence |
|---|---|---|
| Runtime bootstrap boundary | `dpost` runtime bootstrap currently imports/delegates to legacy bootstrap module path. | `src/dpost/runtime/bootstrap.py` references `ipat_watchdog.core.app.bootstrap` |
| Composition boundary typing | `dpost` composition currently keeps legacy bootstrap type coupling via type-check imports. | `src/dpost/runtime/composition.py` TYPE_CHECKING import from legacy bootstrap |
| Architecture direction gap | Current architecture baseline still describes composition delegating runtime bootstrap to legacy wiring, which is incompatible with full strangler completion. | `docs/architecture/architecture-baseline.md` migration notes |

## Phase 9 Implementation Posture
- The increment should satisfy two simultaneous outcomes:
  - functional equivalence for startup behavior, processing entry flow, and
    startup error semantics.
  - syntactic simplification by removing transition-only bootstrap indirection
    in favor of native `dpost` contracts with intention-revealing names.
- Any change that introduces additional wrapper layers should be treated as a
  regression unless required by an explicit contract boundary.

## Phase 9 Tests-First Contract Added
- Added migration tests in:
  - `tests/migration/test_phase9_native_bootstrap_boundary.py`
- New failing expectations cover:
  - no legacy bootstrap-module dependency in `src/dpost/runtime/bootstrap.py`
  - no legacy bootstrap-module/type dependency in
    `src/dpost/runtime/composition.py`

## Red-State Verification
- `python -m pytest tests/migration/test_phase9_native_bootstrap_boundary.py`
  -> `2 failed`

## Risks
- Runtime bootstrap decoupling can affect startup exception/context contracts
  used by existing migration tests.
- Boundary cleanup must preserve behavior while removing type/module coupling.
- Over-aggressive restructuring can reduce readability if new indirection is
  introduced during decoupling.

## Open Questions
- Should native `dpost` bootstrap context/settings classes be introduced in one
  increment or staged (types first, behavior second)?
  - Answer: Deferred to implementation increment; tests currently lock boundary
    decoupling outcome only.
- Should syntactic cleanup be optimized in the same increment as bootstrap
  decoupling?
  - Answer: Yes; Phase 9 should target functionally equivalent behavior with
    cleaner native boundary syntax in the same gated increment.
