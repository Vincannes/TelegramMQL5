# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules

BASE_DIR = os.getcwd()

# === PySide6 (minimum nécessaire) ===
hiddenimports = collect_submodules('PySide6')

datas = [
    (os.path.join(BASE_DIR, 'app', 'config', '*.ini'), 'config'),
    (os.path.join(BASE_DIR, 'app', 'ui', '*.ui'), 'ui'),
    (os.path.join(BASE_DIR, 'app', 'ui', 'style.css'), 'ui'),
]

a = Analysis(
    ['main.py'],
    pathex=[BASE_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TelegramToMQL',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=os.path.join(BASE_DIR, 'assets', 'logo_telesignal.ico'),
    onefile=True,
)
