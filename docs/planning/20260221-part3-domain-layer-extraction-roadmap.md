# Part 3 Domain Layer Extraction Roadmap

## Goal
- Populate `src/dpost/domain/` with pure business entities/value objects and
  domain policies, while preserving functional behavior and keeping full test
  gates green.

## Progress Snapshot (2026-02-21)
- Wave 3.2 is complete:
  - processing value models/enums now owned by
    `src/dpost/domain/processing/models.py`
  - routing policy now owned by `src/dpost/domain/processing/routing.py`
  - `src/dpost/application/processing/models.py` retired
- Wave 3.3 is complete:
  - `LocalRecord` now owned by `src/dpost/domain/records/local_record.py`
  - `src/dpost/application/records/local_record.py` retired
  - record parsing no longer depends on direct runtime config accessors inside
    the domain entity
- Wave 3.4 is complete:
  - staged batch value models now owned by
    `src/dpost/domain/processing/batch_models.py`
  - pair-reconstruction/stale-stage policies now owned by
    `src/dpost/domain/processing/staging.py`
  - `src/dpost/application/processing/batch_models.py` retired
- Wave 3.5 is complete:
  - architecture baseline/responsibility docs updated for final ownership state
  - ADR captured at
    `docs/architecture/adr/ADR-0005-domain-processing-and-record-ownership-extraction.md`
- Wave 3.6 is complete:
  - domain modules no longer import `dpost.application`/`dpost.infrastructure`
    for type/logging concerns
  - domain processing now uses domain-local protocols for appendability/device
    references
  - purity guard added at
    `tests/migration/test_part3_domain_purity_boundaries.py`
- Wave 3.7 is complete:
  - text-prefix decode policy now owned by
    `src/dpost/domain/processing/text.py`
  - `src/dpost/application/processing/text_utils.py` retired
  - PSA/Kinexus/DSV processors now consume shared domain text policy helper
  - ownership guard added at
    `tests/migration/test_part3_domain_text_policy_ownership.py`
- Wave 3.8 is complete:
  - filename-prefix validation/sanitization policy now owned by
    `src/dpost/domain/naming/prefix_policy.py`
  - config-aware naming facade now owned by
    `src/dpost/application/naming/policy.py`
  - `src/dpost/infrastructure/storage/filesystem_utils.py` retired direct
    prefix policy ownership
  - ERM Hioki + processing routing/rename flows now consume application/domain
    naming policy modules
  - ownership guard added at
    `tests/migration/test_part3_domain_naming_policy_ownership.py`
- Wave 3.9 is complete:
  - filename parsing and record/file identifier policy now owned by
    `src/dpost/domain/naming/identifiers.py`
  - `src/dpost/application/naming/policy.py` now exposes config-aware
    identifier helpers (`parse_filename`, `generate_record_id`,
    `generate_file_id`)
  - `src/dpost/infrastructure/storage/filesystem_utils.py` retired direct
    parse/identifier policy ownership
  - processing manager and routing/record orchestration now consume
    application/domain naming identifier helpers
  - ownership guard added at
    `tests/migration/test_part3_domain_naming_identifier_ownership.py`
- Remaining Part 3 closure item: manual validation checklist execution.

## Non-Goals
- No runtime entrypoint redesign.
- No plugin behavior redesign.
- No backend/sync feature additions.
- No broad test-suite restructuring outside required import ownership changes.

## Constraints
- Preserve observable behavior (processing, routing, records, sync side
  effects, operator-facing errors).
- Keep layering contract strict:
  - domain: pure rules/models
  - application: orchestration/use cases/ports
  - infrastructure: adapters and side effects
- Execute in checkpointed TDD slices with migration + full gates.

## Approach
- Use framework-first extraction:
  1. define domain contracts/models and write characterization tests,
  2. migrate application orchestration to consume domain modules,
  3. remove superseded application-local model/policy duplicates.
- Prioritize low-coupling moves first to establish stable domain imports.
- Avoid compatibility wrappers unless a transition seam is strictly required.

## Part 3 Extraction Waves
- Wave 3.1: Domain foundation and module topology
  - Create domain subpackages and ownership boundaries:
    - `src/dpost/domain/records/`
    - `src/dpost/domain/processing/`
    - `src/dpost/domain/naming/` (if needed)
  - Add domain-level tests that characterize current behavior before moving
    implementation.

- Wave 3.2: Pure value models and routing policy
  - Move pure processing models/enums from
    `src/dpost/application/processing/models.py` to domain.
  - Split `determine_routing_state` into domain policy helper(s).
  - Keep record lookup/storage and plugin processor orchestration in
    application.

- Wave 3.3: Record entity extraction
  - Move `LocalRecord` to `src/dpost/domain/records/local_record.py`.
  - Remove runtime accessor coupling (`current()`) from entity behavior by
    passing explicit separators/config values from application boundary.
  - Keep persistence/sync orchestration in
    `src/dpost/application/records/record_manager.py`.

- Wave 3.4: Batch/staging/text policy extraction
  - Move `batch_models.py` and pure staging pairing rules to domain processing
    helpers.
  - Keep file IO, filesystem operations, and logger usage at
    application/infrastructure edges.

- Wave 3.5: Contract cleanup and deletion
  - Remove deprecated application-local model/policy duplicates.
  - Update architecture docs and responsibility catalog to reflect final
    ownership.

## Milestones
- M1: Domain package skeleton + first characterization tests are green.
- M2: Routing/value-model extraction complete with no behavior regressions.
- M3: `LocalRecord` domain extraction complete; all record/sync tests green.
- M4: Batch/staging domain policy extraction complete; integration tests green.
- M5: Application layer contains orchestration-only logic for extracted slices.

## Dependencies
- Existing migration + unit + integration test coverage.
- Current architecture governance documents under `docs/architecture/`.
- Contributor alignment via roadmap/checklist/report artifacts.

## Risks and Mitigations
- Risk: circular dependencies during module moves.
  - Mitigation: move pure types first; invert imports through explicit function
    parameters and interfaces.
- Risk: hidden behavior drift in routing/record semantics.
  - Mitigation: add/expand focused characterization tests before each move.
- Risk: overloading a single PR with too many moved modules.
  - Mitigation: checkpoint commits per extraction wave.

## Test Plan
- For each wave:
  - add/adjust focused tests for extracted domain behavior (red -> green),
  - run targeted module suites,
  - run migration suite and full suite gates.
- Required gates per checkpoint:
  - `python -m pytest tests/migration/test_phase9_native_bootstrap_boundary.py`
  - `python -m pytest -m migration`
  - `python -m ruff check .`
  - `python -m black --check .`
  - `python -m pytest`

## Rollout / Validation
- Execute wave-by-wave with checkpoint commits on
  `experiment/autonomous-tdd`.
- Keep architecture docs synchronized in the same commit as ownership changes.
- Leave final operator workflow validation to manual checks at closure.
