# ADR-0003: Canonical Extension Contracts and Legacy Namespace Retirement

## Archive Status
- Historical ADR from pre-V2-only cutover.
- Retained for traceability; active contributor contracts are defined in
  `docs/architecture/extension-contracts.md`.

## Status
- Accepted

## Date
- 2026-02-21

## Context
- Phase 9-13 runtime work moved canonical runtime composition, plugin loading,
  and concrete plugin packages under `src/dpost/**`.
- Legacy plugin namespace/hook compatibility seams increased complexity and
  obscured the canonical contributor surface.
- Contributor documentation still mixed legacy (`ipat_watchdog`) and canonical
  (`dpost`) extension guidance.

## Decision
- Treat `dpost` as the single canonical extension/runtime identity.
- Retire legacy plugin namespace/hook compatibility from canonical dpost paths.
- Publish explicit public extension contracts in
  `docs/architecture/extension-contracts.md` and align architecture/developer
  documentation with those contracts.
- Tighten dpost device plugin protocol expectations to include
  `get_file_processor` alongside `get_config`.

## Alternatives Considered
- Keep dual namespace compatibility indefinitely:
  - rejected because it increases maintenance burden and slows clean-architecture
    closure.
- Defer extension-contract documentation until after cutover:
  - rejected because unclear contributor boundaries would continue to create
    architectural drift risk during active delivery.

## Consequences
- Positive:
  - clearer, stable contributor extension surface for open-source onboarding.
  - lower runtime/plugin loading complexity in canonical paths.
  - stronger type/contract alignment between plugin loader and processor factory.
- Negative:
  - external extensions that still target legacy namespace/hook conventions must
    adopt dpost contracts.
- Neutral:
  - superseded by ADR-0004 retirement closure: `src/ipat_watchdog/**` is now
    removed from source control.

## Implementation Notes
- Retire canonical plugin compatibility seams:
  - remove `src/dpost/plugins/legacy_compat.py`
  - keep `src/dpost/plugins/system.py` canonical-only.
- Enforce boundary tests:
  - no `ipat_watchdog` namespace literals in `src/dpost/**`.
  - device plugin protocol requires processor accessor contract.
- Update contributor-facing architecture docs and developer guide.

## References
- `docs/architecture/extension-contracts.md`
- `docs/architecture/architecture-contract.md`
- `docs/reports/archive/20260221-phase10-13-runtime-boundary-progress.md`
- `docs/checklists/archive/20260221-dpost-full-legacy-decoupling-clean-architecture-checklist.md`
