# Checklist: V2 Manual PC/Device Pair Bring-Up

## Why this matters
- Verifies `dpost` V2 startup is usable from the real CLI path.
- Verifies plugin discovery, profile activation, and concrete device/PC plugin contracts.
- Establishes a repeatable operator runbook before wiring full end-to-end ingestion.

## Manual Check
- [ ] Run preflight and confirm clean branch state.
- [ ] Validate V2 CLI launch baseline.
- [ ] Validate plugin discovery and `prod` profile activation.
- [ ] Validate concrete device processor behavior (`psa_horiba`).
- [ ] Validate concrete PC sync adapter behavior (`horiba_blb`).
- [ ] Run targeted tests and lint for regression guard.
- [ ] Record outputs and observed drift in completion notes.

## Baseline Context
- Branch: `rewrite/v2-manual-pc-device-bringup`
- Expected runtime mode: `v2`
- Expected profile for this run: `prod`

## Step 1: Preflight
- [ ] `cd D:\Repos\d-post`
- [ ] `git rev-parse --abbrev-ref HEAD`
  - Pass criteria: `rewrite/v2-manual-pc-device-bringup`
- [ ] `git status --short --branch`
  - Pass criteria: clean working tree
- [ ] `python --version`
  - Pass criteria: Python available in active shell

## Step 2: Clear environment overrides
- [ ] `Remove-Item Env:\DPOST_MODE -ErrorAction SilentlyContinue`
- [ ] `Remove-Item Env:\DPOST_PROFILE -ErrorAction SilentlyContinue`
- [ ] `Remove-Item Env:\DPOST_CONFIG -ErrorAction SilentlyContinue`
  - Pass criteria: no override-related startup surprises

## Step 3: CLI baseline launch
- [ ] `python -m dpost --help`
  - Pass criteria: help renders with `--mode {v2}`
- [ ] `python -m dpost --mode v2 --profile prod --headless --dry-run`
  - Pass criteria: startup succeeds
- [ ] `python -m dpost --mode v2 --profile prod --headless`
  - Pass criteria: startup succeeds

## Step 4: Discovery baseline
- [ ] `python -c "from dpost_v2.plugins.discovery import discover_from_namespaces as f; r=f(); print('devices=', [d.plugin_id for d in r.descriptors if d.family=='device']); print('pcs=', [d.plugin_id for d in r.descriptors if d.family=='pc'])"`
  - Pass criteria: includes `psa_horiba` in devices and `horiba_blb` in pcs

## Step 5: Activate prod profile
- [ ] `python -c "from dpost_v2.plugins.discovery import discover_from_namespaces; from dpost_v2.plugins.host import PluginHost; h=PluginHost(discover_from_namespaces().descriptors); s=h.activate_profile(profile='prod', known_profiles={'prod'}); print('active_devices=', s.selected_by_family['device']); print('active_pcs=', s.selected_by_family['pc'])"`
  - Pass criteria: active lists include `psa_horiba` and `horiba_blb`

## Step 6: Device processor smoke (`psa_horiba`)
- [ ] Run:
```powershell
@'
from datetime import UTC, datetime
from dpost_v2.plugins.discovery import discover_from_namespaces
from dpost_v2.plugins.host import PluginHost
from dpost_v2.application.contracts.context import RuntimeContext, ProcessingContext

h = PluginHost(discover_from_namespaces().descriptors)
h.activate_profile(profile="prod", known_profiles={"prod"})
p = h.create_device_processor("psa_horiba", settings={})
prepared = p.prepare({"source_path":"D:/incoming/horiba_batch.ngb"})
ctx = RuntimeContext.from_settings(
    settings={"mode":"headless","profile":"prod","session_id":"s1","event_id":"e1","trace_id":"t1"},
    dependency_ids={"clock":"c1","ui":"u1","sync":"s1"},
)
pc = ProcessingContext.for_candidate(ctx, {"source_path":prepared["source_path"], "event_type":"created", "observed_at":datetime.now(UTC)})
out = p.process(prepared, pc)
print("prepared=", prepared)
print("can_process=", p.can_process(prepared))
print("result=", {"final_path": out.final_path, "datatype": out.datatype})
'@ | python -
```
  - Pass criteria: `can_process=True` and datatype/final_path printed

## Step 7: PC adapter smoke (`horiba_blb`)
- [ ] Run:
```powershell
@'
from dpost_v2.plugins.discovery import discover_from_namespaces
from dpost_v2.plugins.host import PluginHost
from dpost_v2.plugins.catalog import get_plugin
from dpost_v2.application.contracts.context import RuntimeContext

h = PluginHost(discover_from_namespaces().descriptors)
h.activate_profile(profile="prod", known_profiles={"prod"})
d = get_plugin(h.catalog, "horiba_blb")
ctx = RuntimeContext.from_settings(
    settings={"mode":"headless","profile":"prod","session_id":"s1","event_id":"e1","trace_id":"t1"},
    dependency_ids={"clock":"c1","ui":"u1","sync":"s1"},
)
adapter = d.module_exports["create_sync_adapter"]({})
payload = d.module_exports["prepare_sync_payload"]({"record_id":"r-001"}, ctx)
print("adapter=", dict(adapter))
print("payload=", dict(payload))
'@ | python -
```
  - Pass criteria: adapter/payload dictionaries print with expected keys

## Step 8: Regression guard
- [ ] `python -m pytest -q tests/dpost_v2/plugins/test_discovery.py tests/dpost_v2/plugins/test_device_integration.py tests/dpost_v2/runtime`
  - Pass criteria: all pass
- [ ] `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - Pass criteria: all checks passed

## Step 9: Reality check
- [ ] Confirm current CLI path is startup/bootstrap only for now.
  - Expected note: runtime composition still uses `_NoopIngestionEngine`; this is not full watched-file ingestion yet.

## Completion Notes
- How it was done:
- Commands run and results:
- Files changed:
- Risks/assumptions:
