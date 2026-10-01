# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

ROOT_DIR = Path.cwd()

datas = [
    (str(ROOT_DIR / 'desktop' / 'qml'), 'desktop/qml'),
    (str(ROOT_DIR / 'desktop' / 'assets'), 'desktop/assets'),
    (str(ROOT_DIR / 'data'), 'data'),
]

hiddenimports = [
    'PySide6.QtQuick',
    'PySide6.QtQml',
    'PySide6.QtQuickControls2',
    'PySide6.QtWidgets',
    'PySide6.QtGui',
    'PySide6.QtCore',
    'cloudscraper',
    'requests',
    'bs4',
    'decouple',
    'tqdm',
    'desktop.backend.app_bridge',
    'desktop.backend.scraper_service',
    'desktop.backend.image_provider',
    'desktop.backend.library',
    'engine',
    'scraper',
    'utils',
    'config',
    'gdrive_api',
    'browser_manager',
]

a = Analysis(
    ['desktop/main.py'],
    pathex=[str(ROOT_DIR), str(ROOT_DIR / 'desktop')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CGTips-3D',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='CGTips-3D',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='CGTips-3D.app',
        icon=None,
        bundle_identifier='org.cgtips.desktop',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': 'True',
            'LSMinimumSystemVersion': '11.0',
        },
    )
