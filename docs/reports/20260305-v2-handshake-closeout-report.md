# 20260305 V2 Handshake Closeout Report

## Summary

The V2 architecture handshake is now closed for the current runtime-wiring phase.

Headless V2 standalone processing now proves:
- startup -> dependencies -> composition -> runtime execution is live
- PC plugin owns workstation/device scope
- device plugins own processor behavior selection and transform output
- sync backend owns transport
- PC plugin owns sync payload shaping when a workstation is explicitly selected

This is the point where functional parity migration can proceed without relying on
legacy fallback runtime paths.

## Manual Probe Evidence

Probe root:
- `C:\\Users\\fitz\\AppData\\Local\\Temp\\dpost-v2-closeout-7b_a28e4`

Installed runtime bootstrap probes were executed for one file per workstation/device pair.

| PC plugin | Input file | Resolved plugin | Terminal reason | Incoming after run | Processed after run |
|---|---|---|---|---|---|
| `horiba_blb` | `sample.ngb` | `psa_horiba` | `end_of_stream` | empty | `sample.ngb` |
| `tischrem_blb` | `sample.tif` | `sem_phenomxl2` | `end_of_stream` | empty | `sample.tif` |
| `zwick_blb` | `sample.zs2` | `utm_zwick` | `end_of_stream` | empty | `sample.zs2` |

Each probe persisted a sqlite record whose payload `candidate.plugin_id` matched the
expected concrete device plugin.

## Automated Closeout Evidence

Additional runtime smoke proof added in:
- `tests/dpost_v2/runtime/test_composition.py`

New coverage:
- PC-scoped end-to-end processing for:
  - `horiba_blb -> psa_horiba`
  - `tischrem_blb -> sem_phenomxl2`
  - `zwick_blb -> utm_zwick`
- PC-shaped sync payload proof
- immediate sync failure -> `immediate_sync_error` + `sync_status=unsynced`

## Validation

- `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - passed
- `python -m pytest -q tests/dpost_v2/test___main__.py tests/dpost_v2/application/startup tests/dpost_v2/runtime tests/dpost_v2/application/runtime tests/dpost_v2/application/ingestion tests/dpost_v2/plugins`
  - `189 passed`
- `python -m pytest -q tests/dpost_v2`
  - `412 passed`

## Result

The runtime-wiring phase definition of done is effectively satisfied for the
architecture handshake:
- no silent fallback to `default_device` in the composed standalone path
- real file movement and sqlite persistence in headless mode
- deterministic PC scope enforcement
- explicit processor contract execution in ingestion
- sync payload ownership and transport ownership separated correctly

## Deferred

- Device-specific behavioral parity for `sem_phenomxl2`, `psa_horiba`, and `utm_zwick`
- A decision on whether successful sync should persist normalized sync metadata/state
- Contract cleanup for the still-present but now non-authoritative `create_sync_adapter(...)` PC export
