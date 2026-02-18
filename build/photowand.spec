# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Konfiguration fuer Photowand."""

import os
import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Pfad zum Projektverzeichnis
projekt_pfad = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

# Alle PIL-Submodule einschliessen (Decoder fuer JPG, PNG, GIF, etc.)
pil_imports = collect_submodules('PIL')

a = Analysis(
    [os.path.join(projekt_pfad, 'photowand', 'main.py')],
    pathex=[projekt_pfad],
    binaries=[],
    datas=[],
    hiddenimports=[
        'customtkinter',
        'tkinterdnd2',
    ] + pil_imports,
    hookspath=[os.path.dirname(os.path.abspath(SPEC))],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'scipy', 'pandas',
        'IPython', 'notebook', 'pytest',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Photowand',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
