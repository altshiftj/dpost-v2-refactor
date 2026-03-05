# Report: Lane B utm_zwick

## Scope
- Worktree:
  - `.worktrees/laneB-utm-zwick`
- Goal:
  - turn the Zwick parity-spec surface green without reopening shared runtime architecture
- Reference inputs:
  - `docs/checklists/20260305-v2-three-plugin-parity-matrix.md`
  - `src/ipat_watchdog/device_plugins/utm_zwick/**`
  - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/utm_zwick/**`

## Files Changed
- `src/dpost_v2/plugins/devices/utm_zwick/processor.py`
- `tests/dpost_v2/plugins/devices/utm_zwick/test_parity_spec.py`

## Behavior Delivered
- `.zs2` files now stage series state by exact stem.
- Only a matching `.xlsx` becomes processable for the staged series.
- Finalized outputs emit `datatype="xlsx"` with both raw and results artifacts carried through `force_paths`.
- Added parity checks for staged `.zs2` gating and matching `.xlsx` processability.

## Validation
- `python -m pytest -q tests/dpost_v2/plugins/devices/utm_zwick/test_parity_spec.py`
  - before: `5 failed`
  - after: `5 passed`
- `python -m pytest -q tests/dpost_v2/plugins/devices/utm_zwick`
  - `5 passed`
- `python -m ruff check src/dpost_v2/plugins/devices/utm_zwick tests/dpost_v2/plugins/devices/utm_zwick`
  - passed

## Deferred Risks
- TTL/session-end flush remains deferred because V2 still has no first-class deferred/flush token.
- Unique move semantics and overwrite protection remain deferred because processors still do not receive routed record-directory state.
- Staged Zwick state is in-memory only within the current contract surface.
