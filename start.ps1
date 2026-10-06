$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $ScriptDir '.venv'
$Python = Join-Path $Venv 'Scripts\python.exe'
$Requirements = Join-Path $ScriptDir 'requirements.txt'
$Stamp = Join-Path $Venv 'requirements.sha256'

if (-not (Test-Path -LiteralPath $Python)) {
    python -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment' }
}

$Digest = (Get-FileHash -LiteralPath $Requirements -Algorithm SHA256).Hash.ToLowerInvariant()
if (-not (Test-Path -LiteralPath $Stamp) -or (Get-Content -LiteralPath $Stamp -Raw).Trim() -ne $Digest) {
    & $Python -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Run start.ps1 again to retry.' }
    Set-Content -LiteralPath $Stamp -Value $Digest -Encoding ascii
}

& $Python (Join-Path $ScriptDir 'tray_app.py') @args
exit $LASTEXITCODE
