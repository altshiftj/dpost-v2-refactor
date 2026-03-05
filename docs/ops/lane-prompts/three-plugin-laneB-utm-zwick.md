You are working the `laneB-utm-zwick` packet for `dpost_v2`.

Goal:
Implement `utm_zwick` functional parity inside V2 contracts after spec lock is published.

Allowed edits:
- `src/dpost_v2/plugins/devices/utm_zwick/**`
- `tests/dpost_v2/plugins/devices/utm_zwick/**`

Depends on:
- `docs/checklists/20260305-v2-three-plugin-lane0-spec-lock-checklist.md`

Task:
- make Zwick parity-spec tests pass
- keep staged series behavior deterministic

Do not:
- edit shared runtime or ingestion modules
- change SEM or PSA files

Validation:
- targeted Zwick tests

Output:
- files changed
- tests updated
- commands run and results
- residual Zwick risks
