# simulate_sign.ps1
# Securely sign your executable using an encrypted PFX password

# --- SETTINGS ---
$signtool = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
$pfxPath = "C:\Users\jrfit\.signcert\ipat_wd.pfx"
$pfxPassPath = "$env:USERPROFILE\.signcert\pfxpass.txt"  # Encrypted SecureString file

# --- STEP 1: Validate paths ---
if (!(Test-Path $signtool)) {
    Write-Error "signtool.exe not found. Install Windows SDK."
    exit 1
}

if (!(Test-Path "dist\run.exe")) {
    Write-Error "run.exe not found in dist/"
    exit 1
}

if (!(Test-Path $pfxPath)) {
    Write-Error "PFX file not found at $pfxPath"
    exit 1
}

if (!(Test-Path $pfxPassPath)) {
    Write-Error "Password file not found at $pfxPassPath. Run the setup step first."
    exit 1
}

# --- STEP 2: Read and decrypt password securely ---
try {
    $securePass = Get-Content $pfxPassPath | ConvertTo-SecureString
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePass)
    $plainPass = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} catch {
    Write-Error "Failed to decrypt password."
    exit 1
}

# --- STEP 3: Sign the executable ---
Write-Host "Signing dist\run.exe..."
& "$signtool" sign /f "$pfxPath" /p "$plainPass" /tr http://timestamp.digicert.com `
    /td sha256 /fd sha256 "dist\run.exe"

# --- Cleanup sensitive memory ---
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

# --- STEP 4: Check result ---
if ($LASTEXITCODE -ne 0) {
    Write-Error "Signing failed."
    exit 1
}

Write-Host "Signing successful."
