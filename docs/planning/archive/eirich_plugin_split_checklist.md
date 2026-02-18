# Eirich Device Split Refactor Checklist

Goal: split the current Eirich mixer implementation into two distinct device plugins
(one per device) while keeping existing behavior and tests passing.

## 0. Decisions
- [x] Confirm plugin IDs stay as `rmx_eirich_el1` and `rmx_eirich_r01`.
- [x] Choose a shared-code strategy (common module vs. duplicated processor files).
- [x] Decide whether to keep `mix_eirich` as a compatibility shim or remove it.
  - Note: if duplication becomes painful later, extract `EirichProcessorBase` into
    `device_plugins/eirich_common/processor.py` (no `plugin.py` so it will not register).
Notes:
- Selected duplicate processors; no shared base for now.
- Shim removal confirmed.

## 1. New Package Scaffolding
- [x] Create `src/ipat_watchdog/device_plugins/rmx_eirich_el1/`.
- [x] Create `src/ipat_watchdog/device_plugins/rmx_eirich_r01/`.
- [x] Add `__init__.py` in each new package.
Notes:
- Added both package directories with minimal module docstrings.

## 2. Config Split
- [x] Move EL1 config into `rmx_eirich_el1/settings.py`.
- [x] Move R01 config into `rmx_eirich_r01/settings.py`.
- [x] Verify each config has the correct `identifier`, `device_abbr`, and filename pattern.
- [x] Confirm metadata defaults (tags, descriptions) are preserved.
Notes:
- Split the variant mapping into two fixed builders with per-device IDs and patterns.

## 3. Processor Split
- [x] Move or copy `FileProcessorEirich` into each package (or a shared common module).
- [x] Ensure `get_device_id()` matches the plugin ID for each device.
- [x] Confirm filename pattern matching uses the correct config field.
Notes:
- Duplicated the processor into each package with device-specific IDs.
- Updated filename pattern lookup to use `device_config.files.filename_patterns`.

## 4. Plugin Registration
- [x] Add `plugin.py` per package and register only that device.
- [x] Remove or neutralize `mix_eirich/plugin.py` if no longer used.
- [x] Ensure plugin loader can lazily import the new packages by name.
Notes:
- Added new plugin modules under `rmx_eirich_el1` and `rmx_eirich_r01`.
- Removed the old `mix_eirich` plugin module.

## 5. Update References
- [x] Replace `mix_eirich` imports in tests with the new package paths.
- [x] Update any docs or planning notes that reference `mix_eirich`.
- [x] Re-scan the repo for `mix_eirich` and `rmx_eirich` references and adjust.
Notes:
- Updated integration + unit test imports, plus the Eirich planning doc references.

## 6. Tests
- [x] Update unit tests that build configs and processors.
- [x] Update resolver tests that depend on variant selection by filename.
- [x] Update integration flow test to import the new plugin modules.
Notes:
- Unit tests now use per-device config builders and processors.
- Integration test registers both new plugin modules.

## 7. Packaging / Extras
- [x] Add optional dependency keys for `rmx_eirich_el1` and `rmx_eirich_r01` in `pyproject.toml`.
- [x] Decide whether to keep `mix_eirich` as an alias in extras.
Notes:
- Added new extras and removed the `mix_eirich` extra.

## 8. Cleanup
- [x] Remove obsolete `mix_eirich/settings.py` and `mix_eirich/file_processor.py` if fully migrated.
- [x] If keeping a shim, add a short deprecation note.
Notes:
- Deleted the old `mix_eirich` config/processor/plugin modules; no shim retained.

## 9. Validation
- [x] Run unit tests for Eirich processors and resolver logic.
- [x] Run `tests/integration/test_multi_processor_app_flow.py`.
- [x] Smoke test: drop EL1 and R01 files into the watch folder and confirm routing.
Notes:
- User reported unit + integration tests passing and manual routing verified.
