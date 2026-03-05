You are working the `laneA-sem-phenomxl2` packet for `dpost_v2`.

Goal:
Implement `sem_phenomxl2` functional parity inside V2 contracts after spec lock is published.

Allowed edits:
- `src/dpost_v2/plugins/devices/sem_phenomxl2/**`
- `tests/dpost_v2/plugins/devices/sem_phenomxl2/**`

Depends on:
- `docs/checklists/20260305-v2-three-plugin-lane0-spec-lock-checklist.md`

Task:
- make SEM parity-spec tests pass
- keep changes isolated to SEM plugin scope

Do not:
- edit shared runtime or ingestion modules
- change PSA or Zwick files

Validation:
- targeted SEM tests

Output:
- files changed
- tests updated
- commands run and results
- residual SEM risks
