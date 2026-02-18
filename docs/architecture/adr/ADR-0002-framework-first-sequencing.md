# ADR-0002: Framework-first Sequencing for dpost Migration

## Status
- Accepted

## Date
- 2026-02-18

## Context
- Migration work can drift if concrete integrations (device plugins, sync backends) are moved before stable framework contracts exist.
- The project already committed to headless-first and optional sync adapters, but needed explicit sequencing guidance for execution.

## Decision
- Apply framework-first sequencing for migration delivery:
- implement framework kernel and contracts first
- validate with reference implementations second
- migrate concrete plugins/adapters third

## Alternatives Considered
- Concrete-first migration:
- rejected because integration details can hard-code assumptions before framework boundaries are stable.
- Parallel framework and concrete migration:
- rejected for now because it increases coordination overhead and raises regression risk.

## Consequences
- Positive:
- clearer dependency direction and cleaner architecture boundaries
- better testability of framework contracts independent of concrete integrations
- lower rework risk when adding multiple adapters/plugins
- Negative:
- slower visible integration progress in early phases
- requires discipline to keep concrete migrations out of kernel-first phases
- Neutral:
- existing concrete integrations can still be validated through legacy paths until migrated

## Implementation Notes
- Update phase definitions/checklists to include framework-first gates.
- Require migration tests for kernel contracts before concrete adapter/plugin migration.
- Keep no-op/reference implementations available for framework validation paths.

## References
- `docs/architecture/adr/ADR-0001-headless-first-and-optional-sync-adapters.md`
- `docs/planning/20260218-dpost-architecture-tightening-plan.md`
- `docs/checklists/20260218-dpost-architecture-tightening-checklist.md`
- `docs/planning/20260218-dpost-execution-board.md`

