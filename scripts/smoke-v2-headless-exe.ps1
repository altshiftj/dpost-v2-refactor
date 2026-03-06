param(
    [string]$ExePath = "dist\pyinstaller-v2\dpost-v2-headless\dpost-v2-headless.exe"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$resolvedExePath = if ([System.IO.Path]::IsPathRooted($ExePath)) {
    Resolve-Path $ExePath
} else {
    Resolve-Path (Join-Path $repoRoot $ExePath)
}
$probeRoot = Join-Path $env:TEMP ("dpost-v2-frozen-smoke-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
$configRoot = Join-Path $probeRoot "config"
$incomingPath = Join-Path $configRoot "incoming"
$processedPath = Join-Path $configRoot "processed"
$stagingPath = Join-Path $configRoot "tmp"
$configPath = Join-Path $configRoot "dpost-v2.config.json"
$samplePath = Join-Path $incomingPath "sample.tif"

New-Item -ItemType Directory -Force $configRoot, $incomingPath, $processedPath, $stagingPath | Out-Null
Set-Content $samplePath "payload-tif"

@'
{
  "mode": "headless",
  "profile": "prod",
  "paths": {
    "root": ".",
    "watch": "incoming",
    "dest": "processed",
    "staging": "tmp"
  },
  "ui": { "backend": "headless" },
  "sync": { "backend": "noop", "api_token": null },
  "ingestion": {
    "retry_limit": 3,
    "retry_delay_seconds": 1.0
  },
  "naming": { "prefix": "DPOST", "policy": "prefix_only" },
  "plugins": { "pc_name": "tischrem_blb" }
}
'@ | Set-Content $configPath

Write-Host "Executable: $resolvedExePath"
Write-Host "Probe root:  $probeRoot"

$process = Start-Process `
    -FilePath $resolvedExePath `
    -ArgumentList @("--mode", "v2", "--profile", "prod", "--headless", "--config", $configPath) `
    -PassThru `
    -Wait
$processExitCode = $process.ExitCode
if ($processExitCode -ne 0) {
    throw "Frozen executable returned exit code $processExitCode"
}

$processedSamplePath = Join-Path $processedPath "sample.tif"
$databasePath = Join-Path $configRoot "records.sqlite3"

if (-not (Test-Path $processedSamplePath)) {
    throw "Expected processed file missing: $processedSamplePath"
}
if (Test-Path $samplePath) {
    throw "Expected incoming file to be consumed: $samplePath"
}
if (-not (Test-Path $databasePath)) {
    throw "Expected sqlite database missing: $databasePath"
}

$env:DPOST_PROBE_DB = $databasePath
$pluginId = @'
import json
import os
import sqlite3

db_path = os.environ["DPOST_PROBE_DB"]
conn = sqlite3.connect(db_path)
row = conn.execute(
    "select payload_json from records order by record_id limit 1"
).fetchone()
if row is None:
    raise SystemExit("no records persisted")
payload = json.loads(row[0])
print(payload["candidate"]["plugin_id"])
'@ | python -

$pythonExitCode = if (Get-Variable -Name LASTEXITCODE -Scope Global -ErrorAction SilentlyContinue) {
    $global:LASTEXITCODE
} else {
    0
}
if ($pythonExitCode -ne 0) {
    throw "Failed to inspect sqlite record state."
}
if ($pluginId.Trim() -ne "sem_phenomxl2") {
    throw "Expected plugin_id sem_phenomxl2, got: $pluginId"
}

Write-Host "Processed file: $processedSamplePath"
Write-Host "Record store:   $databasePath"
Write-Host "Plugin id:      $pluginId"
