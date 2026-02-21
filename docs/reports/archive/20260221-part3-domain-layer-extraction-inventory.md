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

## Update (Wave 3.5 Complete)
- Governance closure artifacts are aligned with extraction outcomes:
  - architecture baseline and responsibility catalog updated.
  - ADR recorded:
    `docs/architecture/adr/ADR-0005-domain-processing-and-record-ownership-extraction.md`.
- Remaining closure work is manual workflow validation.

## Update (Wave 3.6 Complete)
- Domain purity hardening is complete:
  - `src/dpost/domain/records/local_record.py` now uses stdlib logging instead
    of infrastructure logger imports.
  - `src/dpost/domain/processing/models.py` and
    `src/dpost/domain/processing/routing.py` no longer import application-layer
    types for domain contracts.
- Migration guard added:
  - `tests/migration/test_part3_domain_purity_boundaries.py`.

## Update (Wave 3.7 Complete)
- Text decode policy ownership is now established under domain:
  - `src/dpost/domain/processing/text.py` owns `read_text_prefix`.
  - `src/dpost/application/processing/text_utils.py` has been removed.
- PSA, Kinexus, and DSV processors now reuse the shared domain text helper.
- Migration guard added:
  - `tests/migration/test_part3_domain_text_policy_ownership.py`.

## Update (Wave 3.8 Complete)
- Naming prefix policy ownership is now established under domain:
  - `src/dpost/domain/naming/prefix_policy.py` owns prefix validation,
    sanitation, and violation analysis policy.
  - `src/dpost/application/naming/policy.py` owns config-aware policy facade.
  - `src/dpost/infrastructure/storage/filesystem_utils.py` no longer owns
    naming prefix policy functions.
- Processing routing/rename and ERM Hioki processor now consume application
  naming facade imports instead of infrastructure naming policy helpers.
- Migration guard added:
  - `tests/migration/test_part3_domain_naming_policy_ownership.py`.

## Update (Wave 3.9 Complete)
- Naming identifier policy ownership is now established under domain:
  - `src/dpost/domain/naming/identifiers.py` owns filename parsing and
    record/file identifier composition policy.
  - `src/dpost/application/naming/policy.py` now exposes config-aware
    identifier helper facade functions.
  - `src/dpost/infrastructure/storage/filesystem_utils.py` no longer defines
    `parse_filename`, `generate_record_id`, or `generate_file_id`.
- Processing manager and routing/record orchestration now consume app naming
  facade imports for parse/identifier policy.
- Migration guard added:
  - `tests/migration/test_part3_domain_naming_identifier_ownership.py`.

## Update (Wave 3.10 Complete)
- Staging directory helper ownership is now established under infrastructure:
  - `src/dpost/infrastructure/storage/staging_dirs.py` owns unique stage-dir
    creation behavior.
  - `src/dpost/application/processing/staging_utils.py` has been removed.
- PSA/Kinexus processors now consume infrastructure staging-dir helper imports.
- Migration guard updates:
  - `tests/migration/test_part3_domain_batch_staging_ownership.py` now
    requires application staging helper retirement plus infrastructure staging
    helper ownership.

## Update (Wave 3.11 Complete)
- Canonical source wording cleanup is complete:
  - removed stale "legacy" wording from canonical dpost runtime sources
    (`src/dpost/infrastructure/sync/kadi.py`,
    `src/dpost/application/processing/file_process_manager.py`).
- Migration guard added:
  - `tests/migration/test_part3_canonical_wording_cleanup.py`.

## Update (Wave 3.12 Complete)
- Transitional rename-routing helper retirement is complete:
  - `_ProcessingPipeline._route_with_prefix()` has been removed from
    canonical processing pipeline code.
- Stage-boundary migration tests now assert direct rename-flow seam behavior
  and no longer depend on `_route_with_prefix()` re-entry guards.

## Findings
- Domain ownership is now established for:
  - processing value/routing models (`src/dpost/domain/processing/models.py`,
    `src/dpost/domain/processing/routing.py`)
  - records entity (`src/dpost/domain/records/local_record.py`)
  - batch/staging/text processing policy
    (`src/dpost/domain/processing/batch_models.py`,
    `src/dpost/domain/processing/staging.py`,
    `src/dpost/domain/processing/text.py`)
  - naming prefix policy (`src/dpost/domain/naming/prefix_policy.py`)
  - naming identifier policy (`src/dpost/domain/naming/identifiers.py`)
- Application now owns config-aware naming policy facade at
  `src/dpost/application/naming/policy.py`.
- Infrastructure storage utilities now focus on filesystem/record persistence
  concerns and no longer define prefix/identifier naming policy functions.
- Stage directory creation now lives under infrastructure storage boundaries
  instead of application helper modules.
- Rename-loop orchestration now uses direct stage seams only and no longer
  carries transitional `_route_with_prefix()` helper indirection.
- Human manual workflow validation was reported complete on 2026-02-21.

## Evidence
- `src/dpost/domain/__init__.py`
- `src/dpost/domain/records/local_record.py`
- `src/dpost/domain/processing/models.py`
- `src/dpost/domain/processing/routing.py`
- `src/dpost/domain/processing/batch_models.py`
- `src/dpost/domain/processing/staging.py`
- `src/dpost/domain/processing/text.py`
- `src/dpost/domain/naming/prefix_policy.py`
- `src/dpost/domain/naming/identifiers.py`
- `src/dpost/application/naming/policy.py`
- `src/dpost/infrastructure/storage/staging_dirs.py`
- `src/dpost/application/processing/routing.py`
- `src/dpost/application/processing/rename_flow.py`
- `src/dpost/device_plugins/erm_hioki/file_processor.py`
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
- No open technical blockers remain for Part 3 code extraction.
- Manual operator/contributor validation closure was reported complete on
  2026-02-21 using:
  - `docs/checklists/archive/20260221-final-manual-validation-runbook.md`.

