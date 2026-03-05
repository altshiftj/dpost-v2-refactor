# 20260305 V2 Three-Plugin Phased Migration Plan (RPC)

## Baseline Confirmed

- Git/worktree is clean on `main`: `## main...origin/main`.
- V2 CLI runtime contract is active: non-dry-run executes `runtime_handle.run()`, dry-run skips runtime in `src/dpost_v2/__main__.py` and covered in `tests/dpost_v2/test___main__.py`.
- Composition uses a real ingestion pipeline and deterministic headless file discovery in `src/dpost_v2/runtime/composition.py` and `tests/dpost_v2/runtime/test_composition.py`.
- Current default startup wiring still builds dict-based backend placeholders in `src/dpost_v2/runtime/startup_dependencies.py`.
- Those placeholders are coerced to fallback runtime shims, including `_PluginHostAdapter` and `_DefaultDeviceProcessor`, in `src/dpost_v2/runtime/composition.py`.
- Runtime processor selection is device-list based and not PC-scoped today in `src/dpost_v2/runtime/composition.py`.
- Ingestion stages currently route/persist without invoking concrete plugin `prepare/process` behavior as the business driver in:
  - `src/dpost_v2/application/ingestion/stages/resolve.py`
  - `src/dpost_v2/application/ingestion/stages/route.py`
  - `src/dpost_v2/application/ingestion/stages/persist.py`
- Target processors are still template subclasses:
  - `src/dpost_v2/plugins/devices/psa_horiba/processor.py`
  - `src/dpost_v2/plugins/devices/sem_phenomxl2/processor.py`
  - `src/dpost_v2/plugins/devices/utm_zwick/processor.py`
- Default headless smoke confirms the gap: one event "succeeds" but source file stays in watch dir, no target file created, resolved plugin is `default_device`.

## Phased Migration Plan (TDD-first, sequential)

| Phase | Red Tests First | Minimal Green Implementation | Exit Gate |
|---|---|---|---|
| 0. Behavior Spec Lock | Add `tests/dpost_v2/plugins/devices/*/test_legacy_parity_spec.py` from historical cases (git `aa1978f^`). | Build parity matrix in `docs/checklists/` mapping each legacy behavior to V2 test IDs. | Explicit accepted/deferred behavior list for each of 3 plugins. |
| 1. Runtime Adapter Hardening | Extend `tests/dpost_v2/runtime/test_startup_dependencies.py` and `tests/dpost_v2/runtime/test_composition.py` to fail unless real adapters are wired (plugin host, file ops, record store, sync). | In `src/dpost_v2/runtime/startup_dependencies.py`, return concrete adapter factories (not dict stubs), initialize `PluginHost` from namespace discovery plus profile activation. | Headless runtime physically moves files and persists records with no fallback host/device path. |
| 2. Ingestion Contract Upgrade | Add failing tests under `tests/dpost_v2/application/ingestion/stages/` proving processor `prepare -> can_process -> process` is executed and influences routing/persist payload. | Add a dedicated transform step (or equivalent) and pass processor output through state; remove selection-only processor usage. | Runtime outcome includes real plugin-derived processing result, not filename passthrough defaults. |
| 3. PC Scope plus Sync Boundary | Add failing runtime/integration tests proving selected PC plugin controls allowed devices and payload shaping (`prepare_sync_payload`), while sync backend only transports. | Add PC-selection policy in startup/runtime context; enforce `active_device_plugins` constraints from PC plugin settings; call PC payload shaping before sync backend. | `horiba_blb -> psa_horiba`, `tischrem_blb -> sem_phenomxl2`, `zwick_blb -> utm_zwick` enforced deterministically. |
| 4. `sem_phenomxl2` Migration | Port legacy tests (trailing-digit normalization, native image handling, ELID zip/descriptor flow). | Implement concrete processor behavior in `src/dpost_v2/plugins/devices/sem_phenomxl2/processor.py`. | Unit plus runtime smoke for SEM pass on real files. |
| 5. `utm_zwick` Migration | Port legacy staging/sentinel/TTL tests from historical `test_file_processor.py` plus integration flow cases. | Implement staged series state (`.zs2` plus sentinel `.xlsx`, TTL flush, unique move semantics) in `src/dpost_v2/plugins/devices/utm_zwick/processor.py`. | Unit plus integration plus runtime smoke pass for repeated series without overwrite regressions. |
| 6. `psa_horiba` Migration | Port legacy bucket/sentinel/purge/reconstruct tests from historical PSA test set. | Implement PSA bucketed pairing, staged flush, sequence naming, zip behavior, stale purge in `src/dpost_v2/plugins/devices/psa_horiba/processor.py`. | Unit plus integration plus runtime smoke pass with deterministic staged processing. |
| 7. Closeout plus Deterministic Headless Gate | Add 3 runtime smoke tests (one per plugin pair) under `tests/dpost_v2/runtime/` using temp watch/dest and asserting filesystem side effects plus emitted events. | Remove or guard fallback adapters so production path cannot silently use `default_device`. Update checklist/report docs. | `python -m pytest -q tests/dpost_v2` and `python -m ruff check src/dpost_v2 tests/dpost_v2` green with documented residual risks. |

## Checks Run During Baseline Capture

- `python -m pytest -q tests/dpost_v2/test___main__.py tests/dpost_v2/runtime/test_composition.py tests/dpost_v2/plugins/test_migration_coverage.py` -> `37 passed`.
- `python -m ruff check src/dpost_v2 tests/dpost_v2` -> passed.

## Notes

- No code files were modified during baseline capture.
- Legacy runtime source for these plugins is removed from working tree, but behavior is recoverable from git history (`aa1978f^`) for parity-driven TDD reconstruction.
