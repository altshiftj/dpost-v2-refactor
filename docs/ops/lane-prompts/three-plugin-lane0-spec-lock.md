You are working the `lane0-spec-lock` packet for `dpost_v2`.

Goal:
Create the post-handshake parity-spec baseline for `sem_phenomxl2`, `utm_zwick`, and `psa_horiba`.

Allowed edits:
- `tests/dpost_v2/plugins/devices/**`
- `docs/checklists/**`
- `docs/reports/**`

Primary reference:
- `src/ipat_watchdog/device_plugins/**`

Task:
- extract legacy behavior from the three reference plugins
- add red parity-spec tests for all three plugins
- publish accepted and deferred behavior notes

Do not:
- implement plugin code in `src/dpost_v2/plugins/devices/**`
- edit shared runtime or ingestion modules

Validation:
- targeted parity-spec test runs only

Output:
- files changed
- tests added
- accepted or deferred behavior summary
- risks or ambiguities
