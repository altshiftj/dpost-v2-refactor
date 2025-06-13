# Shared CI context setup
$ip    = $env:TARGET_IP
$port  = $env:TARGET_PORT
$user  = $env:TARGET_USER
$pass  = $env:TARGET_PASS

$fpr   = "ssh-ed25519 255 SHA256:xUgAlbUoJUxxDPICmiaeZSvGjcwvv4v+rQ9B7axh5TI"
$task  = "IPAT-Watchdog-${env:DEVICE_SLUG}"
$exe   = "C:\\Watchdog\\wd_${env:DEVICE_SLUG}.exe"

function Register-WatchdogTask {
  plink.exe -P $port -batch -pw "$pass" -hostkey "$fpr" "$user@$ip" `
    "powershell -Command `
      \$a=New-ScheduledTaskAction -Execute '$exe'; `
      \$t=New-ScheduledTaskTrigger -AtStartup; `
      Register-ScheduledTask -TaskName '$task' -Action \$a -Trigger \$t -Force; `
      Start-ScheduledTask -TaskName '$task'"
}

function Restore-WatchdogBackup {
  plink.exe -P $port -batch -pw "$pass" -hostkey "$fpr" "$user@$ip" `
    "powershell -Command `
      Stop-ScheduledTask -TaskName '$task' -ErrorAction SilentlyContinue; `
      if(Test-Path '${exe}_backup'){ Copy-Item '${exe}_backup' '${exe}' -Force }; `
      Start-ScheduledTask -TaskName '$task'"
}
