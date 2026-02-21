# Full Legacy Retirement Migration Notes

## Date
- 2026-02-21

## Audience
- Maintainers and contributors updating local workflows after full
  `ipat_watchdog` source retirement.
- Any downstream automation that previously referenced legacy module paths.

## Summary
- Legacy source package `src/ipat_watchdog/**` is retired.
- Canonical runtime and import target is `dpost` only.
- Domain ownership extraction is complete for processing and records:
  - `src/dpost/domain/processing/**`
  - `src/dpost/domain/records/**`

## Breaking Changes
- `ipat_watchdog.*` imports are no longer valid in this repository.
- Legacy runtime entrypoints and package paths are retired.
- Application-local modules superseded by domain ownership were removed:
  - `src/dpost/application/processing/models.py`
  - `src/dpost/application/processing/batch_models.py`
  - `src/dpost/application/processing/text_utils.py`
  - `src/dpost/application/records/local_record.py`
- Naming policy extraction moved prefix helpers out of infrastructure storage:
  - `is_valid_prefix`, `sanitize_prefix`, `sanitize_and_validate`,
    `explain_filename_violation`, and `analyze_user_input` are no longer
    defined in `src/dpost/infrastructure/storage/filesystem_utils.py`
  - canonical ownership is now:
    `src/dpost/domain/naming/prefix_policy.py` and
    `src/dpost/application/naming/policy.py`
- Naming identifier extraction moved parse/ID helpers out of infrastructure
  storage:
  - `parse_filename`, `generate_record_id`, and `generate_file_id` are no
    longer defined in
    `src/dpost/infrastructure/storage/filesystem_utils.py`
  - canonical ownership is now:
    `src/dpost/domain/naming/identifiers.py` and
    `src/dpost/application/naming/policy.py`
- Stage-directory helper ownership moved out of application processing:
  - `src/dpost/application/processing/staging_utils.py` has been removed
  - canonical ownership is now:
    `src/dpost/infrastructure/storage/staging_dirs.py`

## Required Contributor Updates
1. Replace legacy imports with canonical `dpost` imports.
2. Start runtime via `python -m dpost` (or console script `dpost`).
3. Use migration/full quality gates:
   - `python -m pytest -m migration`
   - `python -m pytest`
4. Treat `-m legacy` tests as archived compatibility characterization only.

## Manual Script Portability Note
- `tests/manual/test_plugin_import.py` now uses ASCII markers (`[OK]`, `[FAIL]`)
  to run in default Windows cp1252 terminals.

## Validation Evidence (Latest Checkpoint)
- `python -m pytest tests/migration/test_phase9_native_bootstrap_boundary.py`
- `python -m pytest -m migration`
- `python -m ruff check .`
- `python -m black --check .`
- `python -m pytest`

## Remaining Work
- Manual workflow validation closure was reported complete on 2026-02-21.
