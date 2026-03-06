param(
    [string]$DistPath = "dist\pyinstaller-v2",
    [string]$WorkPath = "build\pyinstaller-v2",
    [switch]$DebugConsole
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$specPath = Join-Path $repoRoot "build\specs\dpost_v2_headless.spec"
$resolvedDistPath = if ([System.IO.Path]::IsPathRooted($DistPath)) {
    $DistPath
} else {
    Join-Path $repoRoot $DistPath
}
$variantWorkLeaf = if ($DebugConsole) {
    "debug-console"
} else {
    "windowless"
}
$resolvedWorkPathBase = if ([System.IO.Path]::IsPathRooted($WorkPath)) {
    $WorkPath
} else {
    Join-Path $repoRoot $WorkPath
}
$resolvedWorkPath = Join-Path $resolvedWorkPathBase $variantWorkLeaf
$previousDebugFlag = if (Test-Path Env:\DPOST_PYINSTALLER_DEBUG_CONSOLE) {
    (Get-Item Env:\DPOST_PYINSTALLER_DEBUG_CONSOLE).Value
} else {
    $null
}

if ($DebugConsole) {
    $env:DPOST_PYINSTALLER_DEBUG_CONSOLE = "1"
    Write-Host "Building debug-console variant."
} else {
    Remove-Item Env:\DPOST_PYINSTALLER_DEBUG_CONSOLE -ErrorAction SilentlyContinue
    Write-Host "Building windowed/background variant."
}

try {
    python -m PyInstaller `
      --noconfirm `
      --clean `
      --distpath $resolvedDistPath `
      --workpath $resolvedWorkPath `
      $specPath
} finally {
    if ($null -eq $previousDebugFlag) {
        Remove-Item Env:\DPOST_PYINSTALLER_DEBUG_CONSOLE -ErrorAction SilentlyContinue
    } else {
        $env:DPOST_PYINSTALLER_DEBUG_CONSOLE = $previousDebugFlag
    }
}
