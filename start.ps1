# Anycubic Cloud Auto-Uploader – Starter
# Richtet die Python-Umgebung ein (einmalig) und startet den Watcher.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv      = Join-Path $ScriptDir ".venv"
$Python    = Join-Path $Venv "Scripts\python.exe"

# Venv anlegen und Abhängigkeiten installieren (einmalig)
if (-not (Test-Path $Python)) {
    Write-Host "Richte Python-Umgebung ein..."
    python -m venv $Venv
    & $Python -m pip install --quiet --upgrade pip
    & $Python -m pip install --quiet -r (Join-Path $ScriptDir "requirements.txt")
    Write-Host "Fertig."
}

# Token holen falls noch keiner gespeichert ist
$ConfigFile = Join-Path $ScriptDir "config.json"
if (-not (Test-Path $ConfigFile) -or
    (Get-Content $ConfigFile | ConvertFrom-Json).token -eq "HIER_DEINEN_TOKEN_EINTRAGEN") {
    Write-Host "Kein Token vorhanden – starte Token-Extraktor..."
    & $Python (Join-Path $ScriptDir "setup_token.py")
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

Write-Host "Starte Anycubic Auto-Uploader (Tray)..."
& $Python (Join-Path $ScriptDir "tray_app.py")
