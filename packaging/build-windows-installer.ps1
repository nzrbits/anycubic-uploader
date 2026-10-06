$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$toolRoot = Join-Path $projectRoot 'build\inno-setup'
$compiler = Join-Path $toolRoot 'ISCC.exe'
if (-not (Test-Path -LiteralPath $compiler)) {
    New-Item -ItemType Directory -Path $toolRoot -Force | Out-Null
    $download = Join-Path $toolRoot 'innosetup-6.7.3.exe'
    Invoke-WebRequest -Uri 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe' -OutFile $download
    $signature = Get-AuthenticodeSignature -LiteralPath $download
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Pyrsys B\.V\.') {
        throw 'Inno Setup download did not pass publisher verification'
    }
    $setup = Start-Process -FilePath $download -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER', '/NOICONS', ('/DIR="' + $toolRoot + '"')) -WindowStyle Hidden -Wait -PassThru
    if ($setup.ExitCode -ne 0) { throw 'Inno Setup installation failed' }
}
& $compiler (Join-Path $PSScriptRoot 'windows.iss')
if ($LASTEXITCODE -ne 0) { throw 'Windows setup compilation failed' }
