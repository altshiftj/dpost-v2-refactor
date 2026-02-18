# dpost Migration Execution Board

## Board Metadata
- Created: 2026-02-18
- Planning horizon: 2026-02-19 to 2026-05-15
- Runtime posture: headless-first
- Sync posture: optional adapter model

## Owner Roles
- Core Owner: Repository maintainer driving architecture and merges.
- Plugin Owner: Maintainer handling plugin hygiene and discovery validation.
- Runtime Owner: Maintainer handling entrypoints, runtime modes, and deployment scripts.
- QA Owner: Maintainer handling gates, regression checks, and manual validation.

## Schedule
| Phase | Window (Start -> Target End) | Owner | Status | Gate to Close |
|---|---|---|---|---|
| Phase 1: Baseline and Contract Freeze | 2026-02-19 -> 2026-02-26 | QA Owner + Core Owner | Planned | Baseline tests green and architecture contract doc linked |
| Phase 2: dpost Spine and Headless Composition Root | 2026-02-27 -> 2026-03-10 | Runtime Owner + Core Owner | In Progress | Headless `dpost` entrypoint smoke test green, legacy entrypoint intact |
| Phase 3: Optional Sync Adapter Interface | 2026-03-11 -> 2026-03-19 | Core Owner | Planned | Sync adapter port active, Kadi adapter optional, adapter-selection tests green |
| Phase 4: Configuration Consolidation | 2026-03-20 -> 2026-03-31 | Core Owner | Planned | Legacy constant fallbacks removed from operational paths |
| Phase 5: Processing Pipeline Decomposition | 2026-04-01 -> 2026-04-15 | Core Owner | Planned | Stage services extracted, integration suite unchanged/green |
| Phase 6: Plugin and Discovery Hardening | 2026-04-16 -> 2026-04-24 | Plugin Owner | Planned | Plugin inventory normalized and discovery tests green |
| Phase 7: Desktop Runtime Integration | 2026-04-27 -> 2026-05-06 | Runtime Owner | Planned | Desktop and headless smoke tests both green |
| Phase 8: Final Cutover and Cleanup | 2026-05-07 -> 2026-05-15 | Core Owner + QA Owner | Planned | `dpost` canonical metadata/docs complete and release gate passed |

## Weekly Cadence
- Monday: phase planning and risk review.
- Wednesday: mid-phase checkpoint against gate criteria.
- Friday: gate readiness check and issue triage.
- Friday (documentation gate): verify baseline/responsibility/ADR/glossary updates for the week.

## Change Control
- Any scope change that affects a closed phase gate requires:
- explicit note in this board
- updated acceptance criteria in the phase checklist
- re-baselined target end date

## Current State (as of 2026-02-18)
- Decisions captured and locked in planning/checklist docs.
- Phase 2 scaffold landed early:
- `src/dpost/` package skeleton exists.
- `dpost` script entrypoint exists in `pyproject.toml`.
- migration entrypoint tests exist under `tests/migration/`.
- marker split is active (`legacy` and `migration`).
