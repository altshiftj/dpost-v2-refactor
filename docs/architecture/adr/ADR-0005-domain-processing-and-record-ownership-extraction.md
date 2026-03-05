# ADR-0005: Domain Processing and Record Ownership Extraction

## Archive Status
- Historical ADR from pre-V2-only cutover.
- Retained for traceability of extraction strategy; active module ownership is
  governed by `docs/architecture/responsibility-catalog.md`.

## Status
- Accepted

## Date
- 2026-02-21

## Context
- After full legacy source retirement, several pure business/value modules were
  still owned under `src/dpost/application/**`.
- This blurred layering boundaries and made it harder to enforce a strict
  clean-architecture split between pure policies/entities and orchestration.
- Part 3 roadmap explicitly targeted domain ownership for:
  - processing value models and routing decisions,
  - record entity behavior (`LocalRecord`),
  - staged batch and pair-reconstruction policy helpers.

## Decision
- Move pure processing value models and routing policy to
  `src/dpost/domain/processing/`.
- Move `LocalRecord` to `src/dpost/domain/records/local_record.py`.
- Move staged batch value types and reconstruction/stale-stage policies to
  `src/dpost/domain/processing/`.
- Retire superseded application-local modules:
  - `src/dpost/application/processing/models.py`
  - `src/dpost/application/processing/batch_models.py`
  - `src/dpost/application/records/local_record.py`
- Keep orchestration and mutation concerns in application/infrastructure
  modules (for example `FileProcessManager`, `RecordManager`,
  `staging_utils.create_unique_stage_dir`).

## Alternatives Considered
- Keep pure models/policies in `application` and document intent only:
  - rejected because boundary violations remain easy to reintroduce.
- Add compatibility wrapper modules in `application` for moved domain modules:
  - rejected as default because wrappers prolong duplicate ownership and drift.

## Consequences
- Positive:
  - clearer layer boundaries with explicit domain ownership for pure behavior.
  - lower risk of orchestration concerns leaking into core policy/entity code.
  - simpler guardrails through ownership-focused boundary tests.
- Negative:
  - broad import rewiring across plugins/tests was required.
  - additional boundary test surfaces increase maintenance overhead.
- Neutral:
  - manual workflow checks remain required at phase closure.

## Implementation Notes
- Added domain ownership modules:
  - `src/dpost/domain/processing/models.py`
  - `src/dpost/domain/processing/routing.py`
  - `src/dpost/domain/processing/batch_models.py`
  - `src/dpost/domain/processing/staging.py`
  - `src/dpost/domain/records/local_record.py`
- Added ownership guards in canonical test suites.
- Updated architecture governance docs and Part 3 roadmap/checklist/report in
  the same change windows.

## References
- `docs/planning/archive/20260221-part3-domain-layer-extraction-roadmap.md`
- `docs/checklists/archive/20260221-part3-domain-layer-extraction-checklist.md`
- `docs/reports/archive/20260221-part3-domain-layer-extraction-inventory.md`

