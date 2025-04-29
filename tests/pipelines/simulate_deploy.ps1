# simulate_deploy.ps1
# Simulate your GitLab "deploy" job locally in PowerShell

# --- SETTINGS ---
$pscpPath = "C:\\Program Files\\PuTTY\\pscp.exe"  # Adjust if different
$targetIP = "127.0.0.1"   # or your local VM IP
$targetUser = "testuser"
$targetPass = "password"
$deployPath = "/C:/WatchdogDeploy/"   # SSH remote path format
$localDeployPath = "C:\WatchdogDeploy"  # Local folder if testing without SSH

# --- TIMER START ---
$startTime = Get-Date

# --- Step 1: Check for run.exe ---
if (-Not (Test-Path "dist/run.exe")) {
    Write-Error "dist/run.exe not found! Build it first."
    exit 1
}
Write-Host "Run.exe is ready."

# --- Step 2: LOCAL deployment if on 127.0.0.1 ---
if ($targetIP -eq "127.0.0.1") {
    Write-Host "Performing local deployment (no SSH)..."
    
    # Ensure deploy folder exists
    if (-Not (Test-Path $localDeployPath)) {
        New-Item -Path $localDeployPath -ItemType Directory -Force | Out-Null
    }

    # Copy files locally
    Copy-Item -Path "dist/run.exe" -Destination "$localDeployPath\run.exe" -Force
    Copy-Item -Path "infra\windows\register_task.ps1" -Destination "$localDeployPath\register_task.ps1" -Force

    # --- TIMER END ---
    $endTime = Get-Date
    $duration = $endTime - $startTime

    Write-Host "Local deployment simulation complete."
    Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration)
    exit 0
}

# --- Step 3: REMOTE deployment if real target ---
if (-Not (Test-Path $pscpPath)) {
    Write-Error "pscp.exe not found. Install PuTTY tools or adjust path."
    exit 1
}
Write-Host "Found pscp.exe."

Write-Host "Deploying run.exe to $targetIP..."

& $pscpPath -batch -pw "$targetPass" "dist/run.exe" "${targetUser}@${targetIP}:${deployPath}/run.exe"
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to copy run.exe."; exit 1 }

& $pscpPath -batch -pw "$targetPass" "infra\windows\register_task.ps1" "${targetUser}@${targetIP}:${deployPath}/register_task.ps1"
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to copy register_task.ps1."; exit 1 }

# --- TIMER END ---
$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host "Deployment simulation complete."
Write-Host ("Elapsed time: {0:hh\:mm\:ss}" -f $duration) #-ForegroundColor Green
