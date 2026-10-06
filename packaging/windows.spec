from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / 'tray_app.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=['pystray._win32', 'PIL._tkinter_finder', 'watchdog.observers.read_directory_changes'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='AnycubicUploader',
    icon=str(ROOT / 'packaging' / 'anycubic.ico'),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    runtime_tmpdir=None,
)
