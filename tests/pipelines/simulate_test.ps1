# simulate_test.ps1

Write-Host "== Simulating TEST stage =="

# Optional cleanup
if (Test-Path ".buildvenv") {
    Remove-Item -Recurse -Force ".buildvenv"
}

# Create virtual environment
python -m venv .buildvenv
. .\.buildvenv\Scripts\Activate.ps1

# Upgrade tools & install dev dependencies
python -m pip install -U pip setuptools wheel
pip install -e .[dev]

# Run pytest
Write-Host "`n== Running pytest =="
pytest tests/ --tb=short --disable-warnings --maxfail=5
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "`nAll tests passed."
} else {
    Write-Error "`nTests failed with exit code $exitCode."
    exit $exitCode
}
