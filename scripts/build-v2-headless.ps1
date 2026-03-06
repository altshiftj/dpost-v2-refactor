param(
    [string]$DistPath = "dist\pyinstaller-v2",
    [string]$WorkPath = "build\pyinstaller-v2"
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$specPath = Join-Path $repoRoot "build\specs\dpost_v2_headless.spec"
$resolvedDistPath = if ([System.IO.Path]::IsPathRooted($DistPath)) {
    $DistPath
} else {
    Join-Path $repoRoot $DistPath
}
$resolvedWorkPath = if ([System.IO.Path]::IsPathRooted($WorkPath)) {
    $WorkPath
} else {
    Join-Path $repoRoot $WorkPath
}

python -m PyInstaller `
  --noconfirm `
  --clean `
  --distpath $resolvedDistPath `
  --workpath $resolvedWorkPath `
  $specPath
