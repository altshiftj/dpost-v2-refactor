# Checklist: V2 Manual Launch + Plugin Discovery Validation

## Why this matters
- Confirms `dpost` is usable in V2-only runtime mode under real shell usage.
- Confirms plugin discovery/selection contracts are consistent with V2 API behavior.
- Preserves a stable manual baseline before starting the next stabilization wave.

## Manual Check
- [x] Validate runtime environment and CLI basics.
- [x] Validate launcher accepts V2 mode and rejects retired modes.
- [x] Validate config-driven startup path.
- [x] Validate plugin discovery API and plugin activation by profile.
- [x] Capture command outputs for this run as the baseline for follow-up checks.

## Baseline Context
- Branch: `rewrite/v2-lane-legacy-cleanup-rebuild`
- Python: `3.12.7`
- Entry points tested from repo root:
  - `python -m dpost`
  - `python -m dpost_v2` (alias-equivalent behavior)

## Check: CLI Baseline
- [x] `python --version`
  - Result: `Python 3.12.7`
- [x] `python -m pip --version`
  - Result observed
- [x] `python -m dpost --help`
  - Result: mode choices now `--mode {v2}` only

## Check: V2 Launch Contract
- [x] `python -m dpost --mode v2 --headless --dry-run`
  - Result: `dpost startup succeeded (mode=v2, profile=default)`
- [x] `python -m dpost --mode v2 --profile default --dry-run`
  - Result: success (same profile)
- [x] `python -m dpost --mode v1`
  - Result: CLI rejects with invalid-choice error
- [x] `python -m dpost --mode shadow`
  - Result: CLI rejects with invalid-choice error
- [x] `python -m dpost --mode v2 --config .\configs\dpost-v2.config.json --headless --dry-run`
  - Result: success
- [x] `python -m dpost --mode v2 --config .\configs\dpost-v2.config.json --headless`
  - Result: success

## Check: Plugin Discovery Contract
- [x] `python -c "from dpost_v2.plugins.discovery import discover_devices; discover_devices()"`
  - Result: fails (no such symbol)
- [x] `python -c "from dpost_v2.plugins.discovery import discover_pcs; discover_pcs()"`
  - Result: fails (no such symbol)
- [x] `python -c "from dpost_v2.plugins.discovery import discover_from_namespaces; r = discover_from_namespaces(); print('devices:', [d.plugin_id for d in r.descriptors if d.family == 'device']); print('pcs:', [d.plugin_id for d in r.descriptors if d.family == 'pc'])"`
  - Result devices: `['dsv_horiba', 'erm_hioki', 'extr_haake', 'psa_horiba', 'rhe_kinexus', 'rmx_eirich_el1', 'rmx_eirich_r01', 'sem_phenomxl2', 'test_device', 'utm_zwick']`
  - Result pcs: `['eirich_blb', 'haake_blb', 'hioki_blb', 'horiba_blb', 'kinexus_blb', 'test_pc', 'tischrem_blb', 'zwick_blb']`
- [x] `python -c "from dpost_v2.plugins.discovery import discover_from_namespaces; from dpost_v2.plugins.host import PluginHost; h = PluginHost(discover_from_namespaces().descriptors); h.activate_profile(profile='prod', known_profiles={'prod'}); print('active devices:', h.get_device_plugins()); print('active pcs:', h.get_pc_plugins())"`
  - Result active devices: `('dsv_horiba', 'erm_hioki', 'extr_haake', 'psa_horiba', 'rhe_kinexus', 'rmx_eirich_el1', 'rmx_eirich_r01', 'sem_phenomxl2', 'test_device', 'utm_zwick')`
  - Result active pcs: `('eirich_blb', 'haake_blb', 'hioki_blb', 'horiba_blb', 'kinexus_blb', 'test_pc', 'tischrem_blb', 'zwick_blb')`
- [x] `python -m dpost --mode v2 --profile prod --headless --dry-run`
  - Result: `dpost startup succeeded (mode=v2, profile=prod)`

## Next Steps
- [ ] Add/verify startup diagnostics visibility for selected profiles and plugin IDs.
- [ ] Validate at least one concrete device+pc runtime path via a temporary config profile override.
- [ ] Run focused test smoke before stability handoff:
  - [ ] `python -m pytest -q tests/dpost_v2/application/startup`
  - [ ] `python -m pytest -q tests/dpost_v2/plugins/test_discovery.py tests/dpost_v2/plugins/test_device_integration.py`
  - [ ] `python -m pytest -q tests/dpost_v2/runtime`
- [ ] Capture a stabilization-wave checkpoint with:
  - [ ] Runtime resilience hardening (idempotent startup/shutdown)
  - [ ] Ingestion failure-path determinism
  - [ ] Observability consistency and startup event quality
  - [ ] CI reliability pass before cleanup/archive operations

## Completion Notes
- Most recent run validated that V2-only CLI mode + plugin discovery surface are working.
- Deprecated public assumptions (e.g., `discover_devices()` / `discover_pcs()`) were confirmed as unsupported in current API; valid calls are via `discover_from_namespaces()` and host/profile activation.
- Keep this checklist as the current launch baseline for the next manual/observability hardening wave.
