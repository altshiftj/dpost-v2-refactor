# Report: Lane C psa_horiba

## Scope
- Worktree:
  - `.worktrees/laneC-psa-horiba`
- Goal:
  - turn the PSA parity-spec surface green while keeping staged behavior local to the PSA plugin
- Reference inputs:
  - `docs/checklists/20260305-v2-three-plugin-parity-matrix.md`
  - `src/ipat_watchdog/device_plugins/psa_horiba/**`
  - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/psa_horiba/**`

## Files Changed
- `src/dpost_v2/plugins/devices/psa_horiba/plugin.py`
- `src/dpost_v2/plugins/devices/psa_horiba/processor.py`
- `src/dpost_v2/plugins/devices/psa_horiba/settings.py`
- `tests/dpost_v2/plugins/devices/psa_horiba/test_parity_spec.py`

## Behavior Delivered
- `.tsv` is now a valid PSA source extension.
- PSA plugin capabilities now advertise preprocess and batch support.
- Processor now stages FIFO NGBs, buckets CSV/NGB pairs, recognizes the sentinel CSV->NGB flush, creates deterministic `.__staged__NN` folders, reconstructs staged batches, emits numbered `.csv` and `.zip` outputs, and purges stale in-memory state conservatively.
- Added parity checks for deterministic stage naming/idempotent restaging and stale pending-NGB purge.

## Validation
- `python -m pytest -q tests/dpost_v2/plugins/devices/psa_horiba/test_parity_spec.py`
  - before: `4 failed`
- `python -m pytest -q tests/dpost_v2/plugins/devices/psa_horiba`
  - after: `4 passed`
- `python -m ruff check src/dpost_v2/plugins/devices/psa_horiba tests/dpost_v2/plugins/devices/psa_horiba`
  - passed

## Deferred Risks
- Shared V2 runtime still has no first-class deferred outcome for incomplete PSA events.
- Exception-bucket moves and rename-cancel whole-folder behavior remain deferred to shared runtime work.
- Broader runtime/composition verification remains part of closeout, not this lane packet.
