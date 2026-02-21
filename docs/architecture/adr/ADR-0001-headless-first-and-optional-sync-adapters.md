# ADR-0001: Headless-first Runtime and Optional Sync Adapters

## Status
- Accepted

## Date
- 2026-02-18

## Context
- The cutover from `ipat_watchdog` to `dpost` needed architectural tightening while preserving behavior.
- Current runtime and sync flows are tightly coupled to desktop/UI defaults and a Kadi-specific backend.
- The project goal is broader open-source usability and support for multiple ELN/database sync backends.

## Decision
- Execute the runtime cutover in a headless-first order.
- Introduce a sync adapter boundary so backend integrations are optional and pluggable.
- Keep desktop runtime integration as a later phase after headless core is stable.

## Alternatives Considered
- Desktop-first cutover:
- rejected because UI coupling can hide core architecture issues and slow adapterization.
- Keep Kadi as mandatory core dependency:
- rejected because it limits extensibility and portability for users with other ELN/database targets.

## Consequences
- Positive:
- clear core/runtime separation for automation and CI use
- easier onboarding of alternative sync backends
- lower long-term coupling in application core
- Negative:
- requires explicit adapter selection and startup error handling paths
- introduces packaging complexity for optional backend dependencies
- Neutral:
- desktop runtime remains supported, but sequencing changes

## Implementation Notes
- Introduce sync adapter port in application layer.
- Move Kadi implementation to optional adapter module path.
- Add tests for:
- runtime without Kadi installed
- runtime with selected Kadi adapter
- unknown adapter selection error
- Track execution in:
- `docs/planning/archive/20260218-dpost-architecture-tightening-plan.md`
- `docs/checklists/archive/20260218-dpost-architecture-tightening-checklist.md`
- `docs/planning/archive/20260218-dpost-execution-board.md`

## References
- `docs/reports/20260218-codebase-overview.md`
- `docs/planning/archive/20260218-dpost-architecture-tightening-plan.md`
- `docs/checklists/archive/20260218-dpost-architecture-tightening-checklist.md`
- `docs/planning/archive/20260218-dpost-execution-board.md`

