# simulate_deploy.ps1
# Simulate GitLab "deploy" job locally or remotely in PowerShell

. "$PSScriptRoot/env.ps1"
Set-Location -Path (Resolve-Path "$PSScriptRoot/../..")

# --- SETTINGS ---
$remotePath = "C:\Watchdog"
$ciJobName  = $env:CI_JOB_NAME
$targetIP   = $env:TARGET_IP
$targetUser = $env:TARGET_USER
$targetPass = $env:TARGET_PASS

if (-not $ciJobName)  { $ciJobName = "run" }
if (-not $targetIP)   { $targetIP = "127.0.0.1" }
if (-not $targetUser) { $targetUser = "testuser" }
if (-not $targetPass) { $targetPass = "password" }

$binaryName = "wd-${ciJobName}.exe"
$distBinaryPath = "dist\$binaryName"

# --- TIMER START ---
$startTime = Get-Date

# --- Step 1: Validate required files ---
if (-Not (Test-Path $distBinaryPath)) {
    Write-Error "$distBinaryPath not found. Run the build first."
    exit 1
}
if (-Not (Test-Path "version.txt")) {
    Write-Error "version.txt not found. Ensure build step ran successfully."
    exit 1
}
Write-Host "All artifacts are ready."

# --- Step 2: LOCAL deployment ---
if ($targetIP -eq "127.0.0.1") {
    Write-Host "Performing local deployment..."

    if (-Not (Test-Path $remotePath)) {
        New-Item -Path $remotePath -ItemType Directory -Force | Out-Null
    }

    try {
        Stop-ScheduledTask -TaskName "IPAT-Watchdog" -ErrorAction SilentlyContinue
        Get-Process $ciJobName -ErrorAction SilentlyContinue | Stop-Process -Force
    } catch {
        Write-Host "Warning: Could not stop existing task or process."
    }

    $files = @($binaryName, "version.txt")
    foreach ($f in $files) {
        $src = Join-Path $remotePath $f
        $bak = $src -replace '\.(\w+)$', '_backup.$1'
        if (Test-Path $src) {
            Copy-Item -Force $src $bak
        }
    }

    Copy-Item -Force $distBinaryPath (Join-Path $remotePath $binaryName)
    Copy-Item -Force "version.txt" (Join-Path $remotePath "version.txt")
    Copy-Item -Force "infra/windows/register_task.ps1" (Join-Path $remotePath "register_task.ps1")

    $duration = (Get-Date) - $startTime
    Write-Host ""
    Write-Host "Local deployment simulation complete."
    Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
    exit 0
}

# --- Step 3: REMOTE deployment ---
if (-not (Get-Command "plink" -ErrorAction SilentlyContinue) -or
    -not (Get-Command "pscp"  -ErrorAction SilentlyContinue)) {
    Write-Error "plink and/or pscp not found in PATH."
    exit 1
}

Write-Host "Performing remote deployment to $targetIP..."

# --- Remote prep script: stop services, backup files, ensure dir ---
$prepTemplate = @'
$path = "{0}"
if (-not (Test-Path $path)) {{
    New-Item -Path $path -ItemType Directory -Force | Out-Null
}}

try {{
    if (Get-ScheduledTask -TaskName "IPAT-Watchdog" -ErrorAction SilentlyContinue) {{
        Stop-ScheduledTask -TaskName "IPAT-Watchdog" -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }}
    Get-Process "{1}" -ErrorAction SilentlyContinue | Stop-Process -Force
}} catch {{
    Write-Host "Could not fully stop old watchdog app."
}}

$files = @("{2}", "version.txt")
foreach ($f in $files) {{
    $src = Join-Path $path $f
    $bak = $src -replace '\.(\w+)$', '_backup.$1'
    if (Test-Path $src) {{
        Copy-Item -Force $src $bak
    }}
}}
'@

$prepScript     = [string]::Format($prepTemplate, $remotePath, $ciJobName, $binaryName)
$encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($prepScript))
$cmd            = "powershell -NoProfile -EncodedCommand $encodedCommand"

& plink -batch -pw "$targetPass" "$targetUser@$targetIP" $cmd | Out-Null

# --- Step 4: Copy files via SCP ---
$copyTargets = @(
    @{ Src = $distBinaryPath;                   Dst = "$remotePath/$binaryName" },
    @{ Src = "version.txt";                     Dst = "$remotePath/version.txt" },
    @{ Src = "infra/windows/register_task.ps1"; Dst = "$remotePath/register_task.ps1" }
)

foreach ($target in $copyTargets) {
    $src = $target.Src
    $dst = $target.Dst -replace '\\', '/'
    $remote = "$targetUser@${targetIP}:$dst"

    & pscp -batch -pw "$targetPass" "$src" "$remote"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to copy $src to $remote"
        exit 1
    }
}

# --- TIMER END ---
$duration = (Get-Date) - $startTime
Write-Host ""
Write-Host "Remote deployment simulation complete."
Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
