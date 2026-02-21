# ADR-0004: Full Legacy Source Package Retirement

## Status
- Accepted

## Date
- 2026-02-21

## Context
- Canonical runtime, processing, sync, and plugin ownership had already moved
  to `src/dpost/**`.
- Unit/integration/manual suites were updated to canonical
  `dpost` imports.
- Remaining legacy source tree under `src/ipat_watchdog/**` duplicated
  implementation and increased maintenance risk with no runtime requirement.

## Decision
- Retire the legacy source package tree by removing `src/ipat_watchdog/**`.
- Treat `src/dpost/**` as the only executable source of truth.
- Update retirement guards so retirement criteria assert legacy source absence
  and canonical `dpost` ownership directly.

## Alternatives Considered
- Keep legacy source package as compatibility wrappers:
  - rejected because it preserves dual ownership and slows clean-architecture
    convergence.
- Retire only plugin subtrees first and defer core deletion:
  - rejected because canonical test/runtime ownership was already complete, so
    partial retention provided little value and extra complexity.

## Consequences
- Positive:
  - eliminates duplicated runtime/plugin/core code paths.
  - reduces architectural drift risk and contributor confusion.
  - simplifies future refactor and dependency analysis to a single source tree.
- Negative:
  - any out-of-repo consumers importing `ipat_watchdog.*` must update imports.
- Neutral:
  - historical delivery/report documents still reference legacy paths as
    archived context.

## Implementation Notes
- Removed legacy package:
  - `src/ipat_watchdog/**`
- Updated retirement contract coverage in canonical test suites.
- Updated architecture governance + retirement planning artifacts in the same
  change set.

## References
- `docs/planning/archive/20260221-full-legacy-repo-retirement-roadmap.md`
- `docs/checklists/archive/20260221-full-legacy-repo-retirement-checklist.md`
- `docs/reports/archive/20260221-full-legacy-repo-retirement-inventory.md`

