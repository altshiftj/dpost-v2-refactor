# Report: Lane A sem_phenomxl2

## Scope
- Worktree:
  - `.worktrees/laneA-sem-phenomxl2`
- Goal:
  - turn the SEM parity-spec surface green without changing shared runtime seams
- Reference inputs:
  - `docs/checklists/20260305-v2-three-plugin-parity-matrix.md`
  - `src/ipat_watchdog/device_plugins/sem_phenomxl2/**`
  - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/sem_phenomxl2/**`

## Files Changed
- `src/dpost_v2/plugins/devices/sem_phenomxl2/processor.py`
- `src/dpost_v2/plugins/devices/sem_phenomxl2/settings.py`

## Behavior Delivered
- `.elid` is now a valid SEM source extension.
- Native image processing strips one trailing digit from the basename before routing.
- Native image outputs emit `datatype="img"`.
- ELID directory processing emits `datatype="elid"` with a ZIP `final_path` and descriptor artifacts carried through `force_paths`.

## Validation
- `python -m pytest -q tests/dpost_v2/plugins/devices/sem_phenomxl2/test_parity_spec.py`
  - before: `3 failed`
  - after: `3 passed`
- `python -m ruff check src/dpost_v2/plugins/devices/sem_phenomxl2 tests/dpost_v2/plugins/devices/sem_phenomxl2`
  - passed

## Deferred Risks
- Shared runtime/persist still does not materialize ELID secondary artifacts end-to-end.
- Descriptor dedupe and collision behavior remains deferred because current shared routing does not expose record-directory-aware allocation to the processor.
