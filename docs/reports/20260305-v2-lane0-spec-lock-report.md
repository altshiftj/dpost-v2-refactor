# Report: V2 Lane0 Spec Lock

## Scope
- Worktree:
  - `.worktrees/lane0-spec-lock`
- Goal:
  - publish red parity-spec tests and a stable behavior matrix for:
    - `sem_phenomxl2`
    - `utm_zwick`
    - `psa_horiba`
- Non-goal:
  - no plugin implementation changes in `src/dpost_v2/plugins/devices/**`

## Legacy Reference Surfaces Used
- Primary source:
  - `src/ipat_watchdog/device_plugins/sem_phenomxl2/**`
  - `src/ipat_watchdog/device_plugins/utm_zwick/**`
  - `src/ipat_watchdog/device_plugins/psa_horiba/**`
- Secondary reference:
  - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/sem_phenomxl2/**`
  - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/utm_zwick/**`
  - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/psa_horiba/**`
  - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/psa_horiba/test_purge_and_reconstruct.py`
  - `tests_legacy_reference/ipat_watchdog/tests/unit/device_plugins/psa_horiba/test_staging_rename_cancel.py`
- Supplemental evidence:
  - `src/ipat_watchdog/device_plugins/psa_horiba/README.md`
  - `src/ipat_watchdog/device_plugins/utm_zwick/docs/filewatch_20260216_114326.csv`
  - `src/ipat_watchdog/device_plugins/utm_zwick/docs/filewatch_20260216_114429.csv`

## Findings
- The three legacy processors are materially more stateful than the current V2 template processors.
- `sem_phenomxl2` fits the current V2 processor contract most cleanly.
- `utm_zwick` and `psa_horiba` both rely on staged multi-event state before final processing.
- The current V2 transform seam has no first-class deferred/staged outcome token; it only has prepare, can-process, and immediate process.
- The current V2 route seam does not provide record-directory-aware allocation information to processors, which limits how cleanly sequence numbering and overwrite protection can be encoded in lane0 tests.

## Lane0 Output
- Added red parity-spec tests:
  - `tests/dpost_v2/plugins/devices/sem_phenomxl2/test_parity_spec.py`
  - `tests/dpost_v2/plugins/devices/utm_zwick/test_parity_spec.py`
  - `tests/dpost_v2/plugins/devices/psa_horiba/test_parity_spec.py`
- Added shared processor-test helper:
  - `tests/dpost_v2/plugins/devices/_helpers.py`
- Published parity matrix:
  - `docs/checklists/20260305-v2-three-plugin-parity-matrix.md`

## Contract-Risk Notes
- `sem_phenomxl2`
  - Main gap is ELID multi-artifact routing and dedupe behavior, not state management.
- `utm_zwick`
  - TTL/session-end flush remains a shared seam risk because V2 has no explicit deferred-to-flush contract yet.
- `psa_horiba`
  - Staging-folder reconstruction, stale purge, and rename-cancel behavior all imply shared staging semantics that current V2 contracts do not yet model explicitly.

## Expected Test Status on Lane0
- The new parity-spec tests are expected to fail against the current template processors.
- That red state is intentional and is the handoff target for lanes A/B/C.

## Handoff
- Plugin lanes should treat `docs/checklists/20260305-v2-three-plugin-parity-matrix.md` as the visible parity target.
- Shared runtime changes should stay centralized if plugin lanes discover that deferred/staged behavior cannot be implemented within the current processor seam alone.
