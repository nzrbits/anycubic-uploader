# Anycubic Cloud Auto-Uploader — Windows Launcher
# Sets up Python venv (once) and starts the tray app.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv      = Join-Path $ScriptDir ".venv"
$Python    = Join-Path $Venv "Scripts\python.exe"

# Create venv and install dependencies (first run only)
if (-not (Test-Path $Python)) {
    Write-Host "Setting up Python environment..."
    python -m venv $Venv
    & $Python -m pip install --quiet --upgrade pip
    & $Python -m pip install --quiet -r (Join-Path $ScriptDir "requirements.txt")
    Write-Host "Done."
}

# Run token setup if config.json is missing or has the placeholder token
$ConfigFile = Join-Path $ScriptDir "config.json"
$NeedsToken = $false
if (-not (Test-Path $ConfigFile)) {
    $NeedsToken = $true
} else {
    $token = (Get-Content $ConfigFile -Raw | ConvertFrom-Json).token
    if (-not $token -or $token -eq "YOUR_ANYCUBIC_TOKEN_HERE") {
        $NeedsToken = $true
    }
}

if ($NeedsToken) {
    Write-Host "No token found — running token setup..."
    & $Python (Join-Path $ScriptDir "setup_token.py")
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

Write-Host "Starting Anycubic Auto-Uploader..."
& $Python (Join-Path $ScriptDir "tray_app.py")
