# Report: V2 PyInstaller Build Baseline

## Summary
- Added one canonical V2 PyInstaller baseline for the headless executable.
- Replaced the legacy packaging assumption that specs should target
  `ipat_watchdog` entrypoints.
- Verified both:
  - unit-level packaging contract coverage
  - a real frozen executable smoke run

## Files Added
- `src/dpost_v2/infrastructure/build/__init__.py`
- `src/dpost_v2/infrastructure/build/pyinstaller_baseline.py`
- `tests/dpost_v2/infrastructure/build/test_pyinstaller_baseline.py`
- `build/specs/dpost_v2_headless.spec`
- `scripts/build-v2-headless.ps1`
- `scripts/smoke-v2-headless-exe.ps1`

## Build Contract
- Canonical entrypoint: `src/dpost/__main__.py`
- Executable name: `dpost-v2-headless`
- Accepted plugin baseline:
  - `dpost_v2.plugins.devices.psa_horiba`
  - `dpost_v2.plugins.devices.sem_phenomxl2`
  - `dpost_v2.plugins.devices.utm_zwick`
  - `dpost_v2.plugins.pcs.horiba_blb`
  - `dpost_v2.plugins.pcs.tischrem_blb`
  - `dpost_v2.plugins.pcs.zwick_blb`

## Build Evidence
- PyInstaller version:
  - `6.8.0`
- Build command:

```powershell
python -m PyInstaller --noconfirm --clean --distpath C:\Users\fitz\AppData\Local\Temp\dpost-v2-pyinstaller-dist-20260306-100537 --workpath C:\Users\fitz\AppData\Local\Temp\dpost-v2-pyinstaller-work-20260306-100537 build/specs/dpost_v2_headless.spec
```

- Dist path:
  - `C:\Users\fitz\AppData\Local\Temp\dpost-v2-pyinstaller-dist-20260306-100537`
- Work path:
  - `C:\Users\fitz\AppData\Local\Temp\dpost-v2-pyinstaller-work-20260306-100537`
- Built executable:
  - `C:\Users\fitz\AppData\Local\Temp\dpost-v2-pyinstaller-dist-20260306-100537\dpost-v2-headless\dpost-v2-headless.exe`

## Frozen Smoke Evidence
- Probe root:
  - `C:\Users\fitz\AppData\Local\Temp\dpost-v2-frozen-smoke-20260306-100653`
- Config path:
  - `C:\Users\fitz\AppData\Local\Temp\dpost-v2-frozen-smoke-20260306-100653\config\dpost-v2.config.json`
- Runtime invocation:

```powershell
& C:\Users\fitz\AppData\Local\Temp\dpost-v2-pyinstaller-dist-20260306-100537\dpost-v2-headless\dpost-v2-headless.exe --mode v2 --profile prod --headless --config C:\Users\fitz\AppData\Local\Temp\dpost-v2-frozen-smoke-20260306-100653\config\dpost-v2.config.json
```

- Input probe:
  - `config\incoming\sample.tif`
- Observed results:
  - `config\processed\sample.tif` exists
  - `config\records.sqlite3` exists
  - sqlite row count: `1`
  - persisted `candidate.plugin_id`: `sem_phenomxl2`

## Why This Matters
- The build surface is now aligned to the canonical V2 command entrypoint.
- Packaging no longer depends on legacy workstation-specific specs.
- Frozen execution already proves the current config anchoring contract against a
  real built artifact.

## Residual Risk
- This is a baseline `onedir` build, not a final workstation installer/service
  package.
- Hidden-import coverage is intentionally scoped to the accepted plugin set, not
  arbitrary third-party plugin distributions.
- Continuous/background frozen posture is still covered by the remaining manual
  workstation closeout section, not by this baseline slice alone.
