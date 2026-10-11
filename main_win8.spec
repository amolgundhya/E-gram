# -*- mode: python ; coding: utf-8 -*-
# Windows 7/8 build (Python 3.7.9 + PyInstaller 5.11.0, see requirements.txt).
# Same as the Windows 10 main.spec, except:
# - no Analysis(optimize=...), which PyInstaller 5 does not accept;
# - pathex=[SPECPATH]: the project root has an __init__.py, so PyInstaller 5
#   would otherwise put only the parent folder on the import path and leave
#   out namuna8, namuna9, Yadi, Utility, ... (PyInstaller 6 adds it itself);
# - hookspath=['pyinstaller_hooks']: hook for the vendored ./msoffcrypto.
# Build: pyinstaller main_win8.spec
import os


a = Analysis(
    ['main.py'],
    pathex=[SPECPATH],
    binaries=[],
    datas=[('static', 'static'), ('uploaded_images', 'uploaded_images'), ('ReportImages', 'ReportImages'), ('templates', 'templates'), ('reports', 'reports')],
    hiddenimports=['sqlalchemy.ext.declarative', 'namuna8', 'namuna9', 'namuna10', 'certificates', 'ferfar', 'location_management', 'reports', 'reportstab', 'LogBook', 'Ghoshawara', 'Yadi', 'JWTapi', 'Utility',
                   # imported lazily (inside functions / try-except), so list them;
                   # msoffcrypto's submodules come from pyinstaller_hooks/
                   'pickle5', 'msoffcrypto'],
    hookspath=[os.path.join(SPECPATH, 'pyinstaller_hooks')],
    hooksconfig={},
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
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
