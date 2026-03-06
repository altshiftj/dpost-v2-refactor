# Runbook: V2 Standalone Manual Closeout

## Goal
- Prove source-mode continuous headless execution processes a file that arrives
  after startup.
- Prove frozen continuous headless execution does the same.
- Confirm persisted record state resolves the expected plugin id.

## Windows
- `Window A`: run the app
- `Window B`: drop files and inspect outputs

## One-Time Setup
Run in both windows:

```powershell
cd D:\Repos\dpost-v2-refactor
. .\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "D:\Repos\dpost-v2-refactor\src"
```

---

## Test 1: Source Continuous Mode

### Window A

```powershell
$probe = Join-Path $env:TEMP ("dpost-v2-source-closeout-" + [guid]::NewGuid().ToString("N"))
$configRoot = Join-Path $probe "config"

New-Item -ItemType Directory -Force $configRoot, "$configRoot\incoming", "$configRoot\processed", "$configRoot\tmp" | Out-Null

@'
{
  "mode": "headless",
  "profile": "prod",
  "runtime": {
    "loop_mode": "continuous",
    "poll_interval_seconds": 0.5,
    "idle_timeout_seconds": 20.0,
    "max_runtime_seconds": 60.0
  },
  "paths": {
    "root": ".",
    "watch": "incoming",
    "dest": "processed",
    "staging": "tmp"
  },
  "ui": { "backend": "headless" },
  "sync": { "backend": "noop", "api_token": null },
  "ingestion": { "retry_limit": 3, "retry_delay_seconds": 1.0 },
  "naming": { "prefix": "DPOST", "policy": "prefix_only" },
  "plugins": { "pc_name": "tischrem_blb" }
}
'@ | Set-Content "$configRoot\dpost-v2.config.json"

Write-Host "PROBE: $probe"
python -m dpost --mode v2 --profile prod --headless --config "$configRoot\dpost-v2.config.json"
```

Expected:
- the app stays resident
- it does not exit immediately
- copy the printed `PROBE:` path

### Window B

Paste the probe path from `Window A`:

```powershell
$probe = "PASTE_PROBE_PATH_HERE"
$configRoot = Join-Path $probe "config"

Set-Content "$configRoot\incoming\late-sem.tif" "payload-tif"
Get-ChildItem "$configRoot\incoming"
```

Wait about 8-10 seconds for `Window A` to return to the prompt.

### Inspect Results

```powershell
$configRoot = Join-Path $probe "config"

Get-ChildItem "$configRoot\incoming"
Get-ChildItem "$configRoot\processed"

$env:DPOST_PROBE_DB = "$configRoot\records.sqlite3"
@'
import json
import os
import sqlite3

conn = sqlite3.connect(os.environ["DPOST_PROBE_DB"])
for row in conn.execute("select payload_json from records order by record_id"):
    payload = json.loads(row[0])
    print({
        "plugin_id": payload["candidate"]["plugin_id"],
        "target_path": payload.get("target_path"),
    })
'@ | python -
```

Expected:
- `incoming` is empty
- `processed` contains `late-sem.tif`
- sqlite shows `plugin_id = sem_phenomxl2`

---

## Test 2: Frozen Continuous Mode (Debug Console)

### Build the Debug Variant

```powershell
pwsh -NoProfile -File .\scripts\build-v2-headless.ps1 -DebugConsole
```

Expected artifact:
- `dist\pyinstaller-v2\dpost-v2-headless-debug\dpost-v2-headless-debug.exe`

### Window A

```powershell
$probe = Join-Path $env:TEMP ("dpost-v2-frozen-closeout-" + [guid]::NewGuid().ToString("N"))
$configRoot = Join-Path $probe "config"

New-Item -ItemType Directory -Force $configRoot, "$configRoot\incoming", "$configRoot\processed", "$configRoot\tmp" | Out-Null

@'
{
  "mode": "headless",
  "profile": "prod",
  "runtime": {
    "loop_mode": "continuous",
    "poll_interval_seconds": 0.5,
    "idle_timeout_seconds": 20.0,
    "max_runtime_seconds": 60.0
  },
  "paths": {
    "root": ".",
    "watch": "incoming",
    "dest": "processed",
    "staging": "tmp"
  },
  "ui": { "backend": "headless" },
  "sync": { "backend": "noop", "api_token": null },
  "ingestion": { "retry_limit": 3, "retry_delay_seconds": 1.0 },
  "naming": { "prefix": "DPOST", "policy": "prefix_only" },
  "plugins": { "pc_name": "tischrem_blb" }
}
'@ | Set-Content "$configRoot\dpost-v2.config.json"

$exe = Resolve-Path .\dist\pyinstaller-v2\dpost-v2-headless-debug\dpost-v2-headless-debug.exe
Write-Host "PROBE: $probe"
& $exe --mode v2 --profile prod --headless --config "$configRoot\dpost-v2.config.json"
```

Expected:
- the frozen app stays resident
- it does not exit immediately
- copy the printed `PROBE:` path

### Window B

Paste the probe path from `Window A`:

```powershell
$probe = "PASTE_PROBE_PATH_HERE"
$configRoot = Join-Path $probe "config"

Set-Content "$configRoot\incoming\late-sem-frozen.tif" "payload-tif"
Get-ChildItem "$configRoot\incoming"
```

Wait about 8-10 seconds for `Window A` to return to the prompt.

### Inspect Results

```powershell
$configRoot = Join-Path $probe "config"

Get-ChildItem "$configRoot\incoming"
Get-ChildItem "$configRoot\processed"

$env:DPOST_PROBE_DB = "$configRoot\records.sqlite3"
@'
import json
import os
import sqlite3

conn = sqlite3.connect(os.environ["DPOST_PROBE_DB"])
for row in conn.execute("select payload_json from records order by record_id"):
    payload = json.loads(row[0])
    print({
        "plugin_id": payload["candidate"]["plugin_id"],
        "target_path": payload.get("target_path"),
    })
'@ | python -
```

Expected:
- `incoming` is empty
- `processed` contains `late-sem-frozen.tif`
- sqlite shows `plugin_id = sem_phenomxl2`

---

## Optional Test 3: Explicit Cancellation

Repeat either continuous-mode test, but press `Ctrl+C` in `Window A` before
dropping a file.

Expected:
- the process exits cleanly
- no hang
- a rerun against the same config still starts normally

---

## Quick Interpretation
- Test 1 passing: source continuous mode is good
- Test 2 passing: frozen continuous mode is good
- Test 3 passing: manual shutdown posture is healthy
