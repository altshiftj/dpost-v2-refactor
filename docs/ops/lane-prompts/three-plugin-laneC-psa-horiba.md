You are working the `laneC-psa-horiba` packet for `dpost_v2`.

Goal:
Implement `psa_horiba` functional parity inside V2 contracts after spec lock is published.

Allowed edits:
- `src/dpost_v2/plugins/devices/psa_horiba/**`
- `tests/dpost_v2/plugins/devices/psa_horiba/**`

Depends on:
- `docs/checklists/20260305-v2-three-plugin-lane0-spec-lock-checklist.md`

Task:
- make PSA parity-spec tests pass
- keep staged pairing and purge behavior deterministic

Do not:
- edit shared runtime or ingestion modules
- change SEM or Zwick files

Validation:
- targeted PSA tests

Output:
- files changed
- tests updated
- commands run and results
- residual PSA risks
