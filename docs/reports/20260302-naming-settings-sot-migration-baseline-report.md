# NamingSettings Single-Source Migration Baseline Report (2026-03-02)

## Title
- Baseline findings and execution order for completing the NamingSettings
  single-source-of-truth migration.

## Date
- 2026-03-02

## Context
- The project already aligned on `NamingSettings` as the canonical naming
  policy owner in `src/dpost/application/config/schema.py`.
- The migration intent and historical rationale were documented in:
  `docs/planning/20260224-naming-settings-single-source-of-truth-rpc.md`.
- Architecture docs now cross-link that RPC, but residual compatibility seams
  remain in naming/storage/sync/plugin paths.

## Findings

### 1. Decision alignment is complete at the documentation level
- The architecture docs and README now explicitly point to the RPC.
- This gives one canonical decision record for separator/pattern ownership and
  migration direction.

### 2. Application naming facade still contains ambient runtime lookups
- `src/dpost/application/naming/policy.py` still resolves naming behavior via
  `current()` fallback wrappers (`_id_separator`, `_filename_pattern`,
  `_current_device`) when explicit context is not passed.
- This remains the main application-layer compatibility seam.

### 3. Storage helpers still retain ambient compatibility wrappers
- `src/dpost/infrastructure/storage/filesystem_utils.py` still includes
  `_active_config()` wrappers for paths/separator defaults.
- Most hot paths now pass explicit context, but fallback behavior remains
  available and can still mask missing wiring in call sites.

### 4. Sync layer still supports separator inference/fallback behavior
- `src/dpost/infrastructure/sync/kadi_manager.py` retains
  `_infer_id_separator_from_record(...)` and default/fallback separator logic.
- This is compatible today, but it prevents a strict explicit-context posture.

### 5. Kinexus/PSA processors still have runtime separator fallback
- `src/dpost/device_plugins/rhe_kinexus/file_processor.py` and
  `src/dpost/device_plugins/psa_horiba/file_processor.py` still include
  `_runtime_id_separator()` (`current()` read) and a final `"-"` fallback on
  runtime errors.
- `configure_runtime_context(...)` injection exists, so this is now a cleanup
  seam rather than a missing capability.

### 6. Core processing path is mostly prepared for final cleanup
- Existing slices already wired explicit separator/pattern/path context through
  key processing, rename, record, and storage flows.
- Remaining work is mainly retirement of compatibility wrappers and fallback
  policies, not broad architecture redesign.

## Evidence
- Decision and migration plan:
  - `docs/planning/20260224-naming-settings-single-source-of-truth-rpc.md`
- Architecture cross-links:
  - `docs/architecture/architecture-contract.md`
  - `docs/architecture/architecture-baseline.md`
  - `docs/architecture/responsibility-catalog.md`
  - `docs/architecture/README.md`
- Residual ambient/fallback seams:
  - `src/dpost/application/naming/policy.py`
  - `src/dpost/infrastructure/storage/filesystem_utils.py`
  - `src/dpost/infrastructure/sync/kadi_manager.py`
  - `src/dpost/device_plugins/rhe_kinexus/file_processor.py`
  - `src/dpost/device_plugins/psa_horiba/file_processor.py`
- Baseline verification command outputs (2026-03-02 local run):
  - `rg -n "current\\(\\)\\.(id_separator|filename_pattern|sample_name_pattern)" src/dpost`
  - `rg -n "def _id_separator_for_record|configure_runtime_context\\(" src/dpost`
  - `rg -n "move_to_exception_folder|move_to_rename_folder|get_record_path\\(" src/dpost`

## Risks
- Removing fallback behavior too early can break direct plugin construction and
  non-runtime test fixtures.
- Partial migration of naming/storage helpers can create mixed explicit/ambient
  behavior that is hard to reason about.
- Kadi separator inference removal without guaranteed record-level separator
  availability could cause identifier drift in sync artifacts.
- Runtime naming-overload renames (`runtime.py`/runtime folder naming) add
  churn; they should stay explicitly scoped as optional/deferred unless bundled
  with related refactors.

## Recommended Execution Order
1. Retire ambient `current()` naming reads in `application/naming/policy.py`
   after verifying all call sites already pass explicit context.
2. Remove ambient config defaults from `filesystem_utils.py` where explicit
   context is already available in application/runtime boundaries.
3. Tighten Kadi separator policy to explicit resolver behavior and remove
   inference fallback once record separator propagation is guaranteed.
4. Remove Kinexus/PSA runtime separator fallback (`current()` + `"-"` fallback)
   and keep only explicit constructor/runtime injection paths.
5. Run full checkpoint (`ruff`, targeted pytest, full unit coverage run) and
   document results in this report/checklist set.

## Open Questions
- Should runtime naming-overload renames in the RPC (for clarity only) be part
  of this migration wave?
  - Answer: Default to deferred unless it unblocks active seam removal.
- Do we keep any compatibility fallback wrappers for one final release window?
  - Answer: Prefer full removal in active paths; if retained, keep clearly
    marked and scope-limited with explicit retirement criteria.

## Progress Update: Section 2 Completed (2026-03-02)
- Intended action:
  - remove ambient naming lookups from `application/naming/policy.py` and move
    runtime callers to explicit naming context.
- Observed outcome:
  - retired `current()` fallback reads from policy facade;
  - switched facade APIs to explicit separator/pattern validation;
  - extended processor runtime-context hook with `filename_pattern`;
  - updated manager runtime context injection and Hioki modified-event behavior
    to rely on injected naming context;
  - updated focused tests for explicit-context expectations.
- Validation:
  - `python -m pytest -q tests/unit/application/naming/test_policy.py tests/unit/device_plugins/erm_hioki/test_file_processor.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_file_process_manager.py tests/unit/application/processing/test_force_paths_kadi_sync.py tests/unit/device_plugins/erm_hioki/test_live_run_sequence.py` -> `65 passed`
  - `python -m pytest -q tests/unit/application/records/test_record_manager.py tests/unit/application/processing/test_routing_helpers.py tests/unit/application/processing/test_file_process_manager_branches.py` -> `51 passed, 1 skipped`
  - `python -m ruff check ...` (changed files in this slice) -> pass

## Progress Update: Sections 3-5 Completed (2026-03-02)
- Intended actions:
  - remove ambient storage defaults from `filesystem_utils.py`,
  - tighten Kadi separator policy to explicit resolver behavior,
  - remove Kinexus/PSA runtime separator fallbacks.
- Observed outcome:
  - storage helpers now require explicit context for record/rename/exception
    paths and persisted-record JSON paths (`id_separator`, `dest_dir`,
    `base_dir`, `json_path`) with fail-fast validation;
  - runtime/composition boundaries now inject explicit naming + storage context
    (`id_separator`, `filename_pattern`, `dest_dir`, `rename_dir`,
    `exception_dir`, `current_device`) into processor runtime hooks;
  - Kadi sync no longer infers separator from record identifier patterns and
    now enforces explicit/valid separator resolver outputs;
  - Kinexus/PSA processor fallback separator logic was retired; separator usage
    now depends on explicit constructor/runtime injection;
  - DSV/UTM runtime context hooks were aligned to explicit runtime context
    propagation and covered in branch tests.
- Validation:
  - `python -m pytest -q tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor_branches.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/utm_zwick/test_file_processor_branches.py` -> `91 passed`
  - `python -m pytest -q tests/unit/application/naming/test_policy.py tests/unit/infrastructure/storage/test_filesystem_utils.py tests/unit/infrastructure/sync/test_sync_kadi.py tests/unit/infrastructure/sync/test_sync_kadi_branches.py tests/unit/device_plugins/rhe_kinexus/test_file_processor.py tests/unit/device_plugins/rhe_kinexus/test_file_processor_branches.py tests/unit/device_plugins/psa_horiba/test_file_processor.py tests/unit/device_plugins/psa_horiba/test_file_processor_branches.py tests/unit/application/processing/test_file_process_manager_branches.py tests/unit/application/processing/test_routing_helpers.py tests/unit/application/records/test_record_manager.py` -> `167 passed, 1 skipped`
  - `python -m pytest --cov=src/dpost --cov-report=term-missing -q tests/unit` -> `729 passed, 1 skipped, 1 warning`, `TOTAL 5391 stmts, 0 miss, 100%`
  - `python -m ruff check .` -> `All checks passed!`
  - `rg -n "ipat_watchdog\\." src/dpost` -> no matches

## Final Status for This Wave
- Sections 1-5 of the migration checklist are complete.
- Section 6 (runtime naming-overload file/folder renames) remains explicitly
  deferred as planned in the RPC.
- Naming policy ownership remains centralized in `NamingSettings` and active
  runtime/storage/sync/plugin paths no longer rely on ambient separator/pattern
  fallback seams targeted by this wave.
