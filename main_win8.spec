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
import sys
from PyInstaller.utils.hooks import collect_submodules

# collect_submodules must be able to import the local packages, wherever the spec is run from.
if SPECPATH not in sys.path:
    sys.path.insert(0, SPECPATH)

# All local packages (some have no __init__.py - namespace packages) and all their
# submodules: main.py auto-registers routers by importing namuna8/namuna9/certificates submodules.
LOCAL_PACKAGES = ['namuna8', 'namuna9', 'namuna10', 'certificates', 'ferfar', 'location_management',
                  'reportstab', 'reportRoute', 'LogBook', 'Ghoshawara', 'Yadi', 'JWTapi', 'Utility']
local_hiddenimports = ['database', 'natural_sort']
for _pkg in LOCAL_PACKAGES:
    _mods = collect_submodules(_pkg)
    if not _mods:
        raise SystemExit("main_win8.spec: package '%s' not found (%s)" % (_pkg, SPECPATH))
    local_hiddenimports += _mods

# Utility/QRcodeGeneration.py and print modules write qrcode.png into <bundle>/reports without
# creating the folder - ship an empty reports folder (.keep so electron-builder keeps it).
_reports_keep = os.path.join(workpath, '_reports_keep')
os.makedirs(_reports_keep, exist_ok=True)
open(os.path.join(_reports_keep, '.keep'), 'w').close()


a = Analysis(
    ['main.py'],
    pathex=[SPECPATH],
    binaries=[],
    # uploaded_images (user photos) and reports (generated output) are NOT packed
    # into the exe, same as the Windows 10 main.spec: the app reads them from the
    # exe's folder (cwd), and packing them would ship our test data to clients.
    datas=[('static', 'static'), ('ReportImages', 'ReportImages'), ('templates', 'templates'),
           (os.path.join(_reports_keep, '.keep'), 'reports')],
    # 'reports' is not a code package (generated report output folder) - no hidden import.
    hiddenimports=['sqlalchemy.ext.declarative'] + local_hiddenimports + [
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
