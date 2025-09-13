param(
  [string]$PlantUmlJar = "plantuml.jar",
  [string]$Source = "../../docs/architecture/processing_pipeline.puml",
  [string]$OutDir = "../../docs/architecture"
)

# Ensure Java is available
try {
  $null = & java -version 2>$null
} catch {
  Write-Error "Java is required to run PlantUML. Please install Java (JRE/JDK)."
  exit 1
}

# Resolve paths
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pumlPath = Resolve-Path -Path (Join-Path $scriptDir $Source)
$outDirPath = Resolve-Path -Path (Join-Path $scriptDir $OutDir)

if (-not (Test-Path $pumlPath)) {
  Write-Error "PlantUML source not found: $pumlPath"
  exit 1
}

Write-Host "Rendering PlantUML -> PNG..."
& java -jar $PlantUmlJar -tpng -o $outDirPath $pumlPath
if ($LASTEXITCODE -ne 0) {
  Write-Error "PlantUML rendering failed with exit code $LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-Host "Done. Check output in: $outDirPath"
