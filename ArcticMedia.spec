# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('app\\static', 'app\\static'), ('app\\templates', 'app\\templates')]
binaries = [('vendor\\ffmpeg\\ffmpeg.exe', '.'), ('vendor\\ffmpeg\\ffprobe.exe', '.')]
hiddenimports = ['aiosqlite', 'sqlalchemy.dialects.sqlite.aiosqlite', 'jose', 'jose.backends.cryptography_backend', 'pydantic_core._pydantic_core', 'greenlet._greenlet', 'run_server', 'app.pairing']
hiddenimports += collect_submodules('jose')
hiddenimports += collect_submodules('cryptography')
hiddenimports += collect_submodules('sqlalchemy.dialects')
tmp_ret = collect_all('pydantic_core')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('greenlet')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ArcticMedia',
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
    icon=['app\\static\\img\\logo-mark-icecap-cutout.ico'],
)
