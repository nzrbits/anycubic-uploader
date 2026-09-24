# PyInstaller spec — macOS .app bundle
# Build: pyinstaller build/macos.spec

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    [str(Path('..') / 'tray_app.py')],
    pathex=[str(Path('.').parent)],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pystray._darwin',
        'AppKit',
        'Foundation',
        'objc',
        'PIL._tkinter_finder',
        'watchdog.observers',
        'watchdog.observers.fsevents',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Anycubic Uploader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    argv_emulation=True,   # required for macOS .app
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Anycubic Uploader',
)

app = BUNDLE(
    coll,
    name='Anycubic Uploader.app',
    icon=None,
    bundle_identifier='com.anycubic.uploader',
    info_plist={
        'NSHighResolutionCapable': True,
        'LSUIElement': True,          # hide from Dock — tray-only app
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
    },
)
