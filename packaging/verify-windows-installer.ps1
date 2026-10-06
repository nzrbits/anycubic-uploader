$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Run installer verification on a disposable GitHub runner' }
$projectRoot = Split-Path -Parent $PSScriptRoot
$setup = Join-Path $projectRoot 'dist\AnycubicUploader-Setup.exe'
$installDir = Join-Path $env:RUNNER_TEMP ('anycubic-install-' + [Guid]::NewGuid().ToString('N'))
$dataDir = Join-Path $env:LOCALAPPDATA 'AnycubicUploader'
$configFile = Join-Path $dataDir 'config.json'
if (Test-Path -LiteralPath $configFile) { throw 'Test settings already exist' }
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
'{"token":"installer-test","watch_folders":[],"watch_extensions":[".pm4u"]}' | Set-Content -LiteralPath $configFile
$configHash = (Get-FileHash -LiteralPath $configFile).Hash
$registryKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{B60D44C5-A5EF-4CE8-9ED4-1BEBB7252B13}_is1'
foreach ($attempt in 1..2) {
    $process = Start-Process -FilePath $setup -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', ('/DIR="' + $installDir + '"')) -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Installation $attempt failed" }
    $installedExe = Join-Path $installDir 'AnycubicUploader.exe'
    if ((Get-FileHash -LiteralPath $installedExe).Hash -ne (Get-FileHash -LiteralPath (Join-Path $projectRoot 'dist\AnycubicUploader.exe')).Hash) { throw 'Installed application differs from the build' }
    if ((Get-FileHash -LiteralPath $configFile).Hash -ne $configHash) { throw 'Setup changed existing settings' }
}
$version = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'version.txt') -Raw).Trim()
if ((Get-ItemProperty -LiteralPath $registryKey).DisplayVersion -ne $version) { throw 'Wrong installed version' }
$shortcutPath = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Anycubic Uploader.lnk'
$shell = New-Object -ComObject WScript.Shell
if ($shell.CreateShortcut($shortcutPath).TargetPath -ne $installedExe) { throw 'Start menu shortcut points elsewhere' }
$uninstaller = Join-Path $installDir 'unins000.exe'
$process = Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -WindowStyle Hidden -Wait -PassThru
if ($process.ExitCode -ne 0) { throw 'Uninstallation failed' }
if ((Test-Path -LiteralPath $installedExe) -or (Test-Path -LiteralPath $shortcutPath) -or (Test-Path -LiteralPath $registryKey)) { throw 'Uninstallation left application files or registration' }
if ((Get-FileHash -LiteralPath $configFile).Hash -ne $configHash) { throw 'Uninstall removed or changed user settings' }
Write-Output 'Windows install, reinstall and uninstall passed; user settings preserved'
