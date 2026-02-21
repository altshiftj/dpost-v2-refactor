# Part 3 Domain Layer Extraction Inventory

## Title
- Baseline inventory for Part 3 clean-architecture domain extraction.

## Date
- 2026-02-21

## Context
- Legacy source retirement is complete (`src/ipat_watchdog/**` removed).
- Next objective is to populate `src/dpost/domain/` with pure business/data
  rules while preserving runtime behavior and test parity.

## Update (Wave 3.2 Complete)
- Domain processing ownership is now established:
  - `src/dpost/domain/processing/models.py` owns processing value models/enums.
  - `src/dpost/domain/processing/routing.py` owns routing decision policy.
  - `src/dpost/application/processing/models.py` has been removed.
- Application processing routing now focuses on record-prefix lookup helpers.
- Integration, migration, and full-suite gates are green after the move.

## Update (Wave 3.3 Complete)
- Record entity ownership is now established under domain:
  - `src/dpost/domain/records/local_record.py` owns `LocalRecord`.
  - `src/dpost/application/records/local_record.py` has been removed.
- Domain entity parsing no longer calls runtime config accessors directly.
- Application/infrastructure boundaries now provide separator context where
  required for persistence/rehydration parity.

## Update (Wave 3.4 Complete)
- Batch/staging policy ownership is now established under domain:
  - `src/dpost/domain/processing/batch_models.py` owns staged batch value
    models.
  - `src/dpost/domain/processing/staging.py` owns pair reconstruction and
    stale-stage policy helpers.
  - `src/dpost/application/processing/batch_models.py` has been removed.
- Application staging helpers now retain stage directory creation only.
- PSA/Kinexus processor tests and migration ownership tests are green after
  import rewiring.

## Findings
- `src/dpost/domain/` is currently empty except `__init__.py`.
- Core business objects still live in `application`:
  - `LocalRecord` lifecycle behavior in
    `src/dpost/application/records/local_record.py`.
  - Routing state models in `src/dpost/application/processing/models.py`.
- Domain decisions are partially mixed with infrastructure/application
  dependencies:
  - `src/dpost/application/processing/routing.py` imports
    `dpost.infrastructure.storage.filesystem_utils`.
  - `src/dpost/application/records/local_record.py` depends on runtime config
    accessor (`current()`) and logging.
- Several modules are strong candidates for immediate domain ownership with low
  dependency friction:
  - `src/dpost/application/processing/batch_models.py`
  - `src/dpost/application/processing/staging_utils.py`
  - `src/dpost/application/processing/text_utils.py` (after logger/adapter
    concerns are isolated).
- Config dataclasses in `src/dpost/application/config/schema.py` include
  behavior (`matches_file`, `should_defer_dir`) that may become domain policy
  once filesystem/runtime coupling seams are made explicit.

## Evidence
- `src/dpost/domain/__init__.py`
- `src/dpost/application/records/local_record.py:19`
- `src/dpost/application/records/local_record.py:42`
- `src/dpost/application/processing/models.py:15`
- `src/dpost/application/processing/models.py:32`
- `src/dpost/application/processing/routing.py:11`
- `src/dpost/application/processing/routing.py:17`
- `src/dpost/application/processing/routing.py:36`
- `src/dpost/application/config/schema.py:246`
- `src/dpost/application/config/schema.py:259`
- `src/dpost/application/config/schema.py:273`

## Risks
- Moving entities without stable contracts can create circular imports between
  `application`, `domain`, and `infrastructure`.
- Behavior drift risk is highest in routing/record-state rules because these
  modules are exercised across plugins and integration flows.
- Over-extraction risk: moving orchestration logic into `domain` would violate
  layer intent and reduce clarity.

## Open Questions
- Which modules should move first for lowest-risk, highest-clarity gains?
  - Answer: start with pure value/policy modules (`processing.models`,
    `batch_models`, pure routing policy helpers), then migrate `LocalRecord`
    once runtime-config coupling is removed.
- Should config schema dataclasses move to `domain` in Part 3?
  - Answer: partially; only pure validation/matching policy should move in
    Part 3. Runtime/environment binding remains application/infrastructure.
- Do we need compatibility shims during moves?
  - Answer: no by default; update imports directly and keep slices small with
    green tests at each checkpoint.
