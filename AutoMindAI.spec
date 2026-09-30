# -*- mode: python ; coding: utf-8 -*-
hiddenimports = ['reportlab.pdfbase._fontdata']

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('knowledge/dtc_database.json', 'knowledge'),
        ('knowledge/pid_metadata.json', 'knowledge'),
        ('assets/automind.png', 'assets'),
        ('assets/automind.ico', 'assets'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'fastapi', 'uvicorn', 'pydantic'],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AutoMindAI',
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
    icon='assets/automind.ico',
    version='assets/version_info.txt',
)
