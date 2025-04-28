# --- register_task.ps1 ---
$taskName = "IPAT-Watchdog"
$exePath = "D:\WatchdogDeploy\run.exe"
$logPath = "D:\WatchdogDeploy\logs\app_output.log"
$userName = "$env:USERNAME"

# Ensure logs directory exists
if (!(Test-Path "D:\WatchdogDeploy\logs")) {
    New-Item -ItemType Directory -Path "D:\WatchdogDeploy\logs"
}

# Remove old task if exists
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create Scheduled Task
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"Start-Process -FilePath '$exePath' -RedirectStandardOutput '$logPath' -RedirectStandardError '$logPath' -NoNewWindow`""

$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartInterval (New-TimeSpan -Seconds 30) `
    -RestartCount 9999 `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal -UserId $userName -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal
