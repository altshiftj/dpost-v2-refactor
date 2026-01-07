param(
    [Parameter(Mandatory = $true)]
    [string]$Path,                         # Directory to watch

    [string]$LogPath,                      # Optional path to CSV log

    [string]$Filter = '*',                 # File filter (e.g. '*.csv'; '*' to catch everything)

    [switch]$IncludeSubdirectories         # Include subdirectories
)

# --- Clean up any old handlers from previous runs in this session ---
"FileCreated","FileChanged","FileDeleted","FileRenamed","FileError" | ForEach-Object {
    Unregister-Event -SourceIdentifier $_ -ErrorAction SilentlyContinue
}

# Resolve and validate the path
try {
    $resolvedPath = (Resolve-Path -Path $Path).Path
} catch {
    Write-Error "Path '$Path' does not exist."
    exit 1
}

# Default log file if none provided
if (-not $LogPath) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $LogPath = Join-Path -Path (Get-Location) -ChildPath "filewatch_$timestamp.csv"
}

Write-Host "Watching:              $resolvedPath"
Write-Host "Logging to:            $LogPath"
Write-Host "Filter:                $Filter"
Write-Host "Include subdirectories: $($IncludeSubdirectories.IsPresent)"
Write-Host ""
Write-Host "Press Ctrl+C to stop."
Write-Host ""

# Ensure log file has a header
if (-not (Test-Path $LogPath)) {
    "Timestamp,EventType,Name,FullPath,OldFullPath,Extension,Length,CreationTime,LastWriteTime" |
        Out-File -FilePath $LogPath -Encoding UTF8
}

# Helper: safely get file info (file may disappear quickly)
function Get-FileInfoSafe {
    param([string]$FullPath)

    if (Test-Path -LiteralPath $FullPath -PathType Leaf) {
        try {
            return Get-Item -LiteralPath $FullPath -ErrorAction Stop
        } catch {
            return $null
        }
    }
    return $null
}

# Common handler for all events
function Write-LogRecord {
    param(
        [string]$EventType,
        $SourceEventArgs
    )

    $now = Get-Date
    $fullPath = $SourceEventArgs.FullPath
    $name = $SourceEventArgs.Name
    $oldFullPath = $null

    if ($EventType -eq 'Renamed') {
        # For renamed events
        $oldFullPath = $SourceEventArgs.OldFullPath
    }

    $fileInfo = Get-FileInfoSafe -FullPath $fullPath

    if ($fileInfo) {
        $extension     = $fileInfo.Extension
        $length        = $fileInfo.Length
        $creationTime  = $fileInfo.CreationTime
        $lastWriteTime = $fileInfo.LastWriteTime
    } else {
        # File might not exist (Deleted) or not yet readable (Created)
        $extension     = ''
        $length        = ''
        $creationTime  = $null
        $lastWriteTime = $null
    }

    $creationTimeStr  = if ($creationTime)  { $creationTime.ToString("o") }  else { "" }
    $lastWriteTimeStr = if ($lastWriteTime) { $lastWriteTime.ToString("o") } else { "" }

    # Build CSV line manually for speed & portability
    $line = '"{0}","{1}","{2}","{3}","{4}","{5}",{6},"{7}","{8}"' -f `
        $now.ToString("o"), `
        $EventType, `
        $name.Replace('"', '""'), `
        $fullPath.Replace('"', '""'), `
        ($oldFullPath -replace '"','""'), `
        $extension, `
        ($length -as [string]), `
        $creationTimeStr, `
        $lastWriteTimeStr

    Add-Content -Path $LogPath -Value $line

    # Console feedback
    Write-Host ("[{0}] {1} - {2}" -f $now.ToString("HH:mm:ss"), $EventType, $fullPath)
}

# --- Set up FileSystemWatcher ---
$fsw = New-Object System.IO.FileSystemWatcher
$fsw.Path = $resolvedPath
$fsw.Filter = $Filter
$fsw.IncludeSubdirectories = [bool]$IncludeSubdirectories
$fsw.NotifyFilter = [IO.NotifyFilters]'FileName, DirectoryName, LastWrite, Size, CreationTime'

# Increase buffer a bit (default is 8 KB); must be multiple of 4 KB
$fsw.InternalBufferSize = 64KB

# --- Register event handlers with safety wrappers ---
$handlers = @()

$handlers += Register-ObjectEvent -InputObject $fsw -EventName Created -SourceIdentifier "FileCreated" -Action {
    try {
        Write-LogRecord -EventType 'Created' -SourceEventArgs $Event.SourceEventArgs
    } catch {
        Write-Host "ERROR in Created handler: $($_.Exception.Message)"
    }
}

$handlers += Register-ObjectEvent -InputObject $fsw -EventName Changed -SourceIdentifier "FileChanged" -Action {
    try {
        Write-LogRecord -EventType 'Changed' -SourceEventArgs $Event.SourceEventArgs
    } catch {
        Write-Host "ERROR in Changed handler: $($_.Exception.Message)"
    }
}

$handlers += Register-ObjectEvent -InputObject $fsw -EventName Deleted -SourceIdentifier "FileDeleted" -Action {
    try {
        Write-LogRecord -EventType 'Deleted' -SourceEventArgs $Event.SourceEventArgs
    } catch {
        Write-Host "ERROR in Deleted handler: $($_.Exception.Message)"
    }
}

$handlers += Register-ObjectEvent -InputObject $fsw -EventName Renamed -SourceIdentifier "FileRenamed" -Action {
    try {
        Write-LogRecord -EventType 'Renamed' -SourceEventArgs $Event.SourceEventArgs
    } catch {
        Write-Host "ERROR in Renamed handler: $($_.Exception.Message)"
    }
}

# Error event (buffer overflows, etc.)
$handlers += Register-ObjectEvent -InputObject $fsw -EventName Error -SourceIdentifier "FileError" -Action {
    $ex = $Event.SourceEventArgs.GetException()
    Write-Host "FILE WATCHER ERROR: $($ex.Message)"
}

# Start watching
$fsw.EnableRaisingEvents = $true

# Keep script running until Ctrl+C
try {
    while ($true) {
        Wait-Event -Timeout 1 | Out-Null
    }
} finally {
    # Cleanup
    foreach ($h in $handlers) {
        Unregister-Event -SourceIdentifier $h.Name -ErrorAction SilentlyContinue
    }
    $fsw.Dispose()
}


# PS D:\Repos\ipat_data_watchdog\tools> powershell -ExecutionPolicy Bypass -File .\watch-filedrops.ps1 `
# >>     -Path "C:\Users\fitz\Desktop\Upload" `
# >>     -IncludeSubdirectories