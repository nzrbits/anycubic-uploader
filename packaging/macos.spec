from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / 'tray_app.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=['pystray._darwin', 'AppKit', 'Foundation', 'objc',
                   'PIL._tkinter_finder', 'watchdog.observers.fsevents'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='Anycubic Uploader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    argv_emulation=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name='Anycubic Uploader')
app = BUNDLE(
    coll,
    name='Anycubic Uploader.app',
    bundle_identifier='com.anycubic.uploader',
    info_plist={'NSHighResolutionCapable': True, 'LSUIElement': True,
                'CFBundleShortVersionString': '1.1.0', 'CFBundleVersion': '1.1.0'},
)
