# simulate_deploy.ps1
# Simulate your GitLab "deploy" job locally in PowerShell

# --- SETTINGS ---
$pscpPath = "C:\Program Files\PuTTY\pscp.exe"
$plinkPath = "C:\Program Files\PuTTY\plink.exe"
$targetIP = "127.0.0.1"
$targetUser = "testuser"
$targetPass = "password"
$remotePath = "C:\Watchdog"
$deployPath = "$remotePath\"  # Local or remote depending on IP

# --- TIMER START ---
$startTime = Get-Date

# --- Step 1: Validate required files ---
if (-Not (Test-Path "dist/run.exe")) {
    Write-Error "dist/run.exe not found! Build it first."
    exit 1
}
if (-Not (Test-Path "version.txt")) {
    Write-Error "version.txt not found! Ensure build step ran successfully."
    exit 1
}
Write-Host "All artifacts are ready."

# --- Step 2: LOCAL deployment ---
if ($targetIP -eq "127.0.0.1") {
    Write-Host "Performing local deployment..."

    if (-Not (Test-Path $remotePath)) {
        New-Item -Path $remotePath -ItemType Directory -Force | Out-Null
    }

    # Stop any running scheduled task or process
    try {
        Stop-ScheduledTask -TaskName "IPAT-Watchdog" -ErrorAction SilentlyContinue
        Get-Process run -ErrorAction SilentlyContinue | Stop-Process -Force
    } catch {
        Write-Host "Warning: Could not stop existing task or process."
    }

    # Backup old binary and version
    if (Test-Path "${remotePath}\run.exe") {
        Copy-Item -Force "$remotePath\run.exe" "${remotePath}\run_backup.exe"
    }
    if (Test-Path "${remotePath}\version.txt") {
        Copy-Item -Force "${remotePath}\version.txt" "${remotePath}\version_backup.txt"
    }

    # Copy new files
    Copy-Item -Force "dist/run.exe" "${remotePath}\run.exe"
    Copy-Item -Force "version.txt" "${remotePath}\version.txt"
    Copy-Item -Force "infra\windows\register_task.ps1" "${remotePath}\register_task.ps1"

    $endTime = Get-Date
    $duration = $endTime - $startTime
    Write-Host "Local deployment simulation complete."
    Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
    exit 0
}

# --- Step 3: REMOTE deployment ---
if (-Not (Test-Path $pscpPath) -or -Not (Test-Path $plinkPath)) {
    Write-Error "PuTTY tools not found. Install pscp.exe and plink.exe or adjust paths."
    exit 1
}

Write-Host "Performing remote deployment to ${targetIP}..."

# Optional: Stop task and process remotely
& $plinkPath -batch -pw "${targetPass}" "${targetUser}@${targetIP}" `
    "powershell -NoProfile -ExecutionPolicy Bypass -Command `
        try {
            if (Get-ScheduledTask -TaskName 'IPAT-Watchdog' -ErrorAction SilentlyContinue) {
                Stop-ScheduledTask -TaskName 'IPAT-Watchdog' -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 2
            }
            Get-Process run -ErrorAction SilentlyContinue | Stop-Process -Force
        } catch {
            Write-Host 'Could not fully stop old watchdog app.'
        }"

# Backup current run.exe and version.txt
& $plinkPath -batch -pw "${targetPass}" "${targetUser}@${targetIP}" `
    "powershell -NoProfile -ExecutionPolicy Bypass -Command `
        if (Test-Path '${remotePath}\run.exe') {
            Copy-Item -Force '${remotePath}\run.exe' '${remotePath}\run_backup.exe'
        }
        if (Test-Path '${remotePath}\version.txt') {
            Copy-Item -Force '${remotePath}\version.txt' '${remotePath}\version_backup.txt'
        }"

# Copy new files
& $pscpPath -batch -pw "${targetPass}" "dist/run.exe" "${targetUser}@${targetIP}:${remotePath}\run.exe"
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to copy run.exe"; exit 1 }

& $pscpPath -batch -pw "${targetPass}" "version.txt" "${targetUser}@${targetIP}:${remotePath}\version.txt"
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to copy version.txt"; exit 1 }

& $pscpPath -batch -pw "${targetPass}" "infra\windows\register_task.ps1" "${targetUser}@${targetIP}:${remotePath}\register_task.ps1"
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to copy register_task.ps1"; exit 1 }

# --- TIMER END ---
$endTime = Get-Date
$duration = $endTime - $startTime
Write-Host "Remote deployment simulation complete."
Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
