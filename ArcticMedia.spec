# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Hidden imports for FastAPI, Uvicorn, and SQLAlchemy
hidden_imports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi.applications',
    'fastapi.routing',
    'fastapi.staticfiles',
    'fastapi.templating',
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.ext.asyncio',
    'aiosqlite',
    'jinja2',
    'pydantic_settings',
    'hypercorn.logging',
    'hypercorn.asyncio',
    'hypercorn.protocol.http_stream',
    'hypercorn.protocol.h2',
    'hypercorn.middleware',
    'PIL._tkinter_guess_py',
    'pystray',
    'jose',
    'passlib.handlers.bcrypt',
    'argon2',
    'requests',
    'itsdangerous',
    'httpx',
    'slugify',
]

# Add all submodules from our app to be safe
hidden_imports += collect_submodules('app')

# Include static files and templates
datas = [
    ('app/static', 'app/static'),
    ('app/templates', 'app/templates'),
]

# Analysis for the GUI / Dispatcher
a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
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
    icon=['app/static/img/logo-mark-icecap-cutout.ico'],
)
