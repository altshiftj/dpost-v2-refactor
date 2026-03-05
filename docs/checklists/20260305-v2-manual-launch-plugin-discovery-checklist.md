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
- [x] `python -m dpost --mode v2 --config .\configs\dpost-v2-prod.config.json --headless --dry-run`
  - Result: success
- [x] `python -m dpost --mode v2 --config .\configs\dpost-v2-prod.config.json --headless --dry-run --profile prod`
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

### Check: Config Merge and Effective Profile
- [x] `python -c "from dpost_v2.application.startup.bootstrap import BootstrapRequest; from dpost_v2.application.startup.settings_service import load_startup_settings; from pathlib import Path; request = BootstrapRequest(mode='v2', profile=None, trace_id='manual', metadata={'config_path':'configs/dpost-v2-prod.config.json'}); result = load_startup_settings(request, root_hint=Path('.')); print(result.settings.profile, result.settings.mode)"`
  - Result: `prod headless`
  - Confirms file-based profile is active even when CLI request defaults to `mode=v2/profile=default`.
  - Extended check: effective provenance now tracks file-backed overrides for profile/path/sync/naming fields and mode selection.

## Next Steps
- [x] Add/verify startup diagnostics visibility for selected profiles and plugin IDs.
  - [x] Confirmed via runtime output and `provenance` printout from `load_startup_settings`.
- [x] Validate concrete device+pc runtime path via profile override.
  - [x] Confirmed through:
    - `python -m dpost --mode v2 --profile prod --headless --dry-run` → success
    - `PluginHost(...).get_device_plugins()` includes expected device IDs and PC IDs
    - `host.create_device_processor('test_device', ...)` succeeds
    - `test_pc.create_sync_adapter({})` returns parsed endpoint/payload
- [x] Run focused test smoke before stability handoff:
  - [x] `python -m pytest -q tests/dpost_v2/application/startup`
    - Result: `28 passed in 0.27s`
  - [x] `python -m pytest -q tests/dpost_v2/plugins/test_discovery.py tests/dpost_v2/plugins/test_device_integration.py`
    - Result: `7 passed in 0.20s`
  - [x] `python -m pytest -q tests/dpost_v2/runtime`
    - Result: `12 passed in 0.10s`
- [ ] Capture a stabilization-wave checkpoint with:
  - [ ] Runtime resilience hardening (idempotent startup/shutdown)
  - [ ] Ingestion failure-path determinism
  - [ ] Observability consistency and startup event quality
  - [ ] CI reliability pass before cleanup/archive operations

## Completion Notes
- Most recent run validated that V2-only CLI mode + plugin discovery surface are working.
- Config-file source now wires successfully into startup merge path.
- Deprecated public assumptions (e.g., `discover_devices()` / `discover_pcs()`) were confirmed as unsupported in current API; valid calls are via `discover_from_namespaces()` and host/profile activation.
- Drift note: CLI banner prints request profile (CLI/env), while effective settings profile comes from merged startup settings and may differ when only config-provided profile is set.
- Open item: effective runtime mode in direct `load_startup_settings` probe can report `headless` from config/metadata in some call paths; this is consistent with current merge precedence but worth watching if/when CLI-mode normalization is hardened further.
- Keep this checklist as the current launch baseline for the next manual/observability hardening wave.
