# Folder (one-dir) build - main.spec ची प्रत, फक्त पॅकिंग बदलले (Nov-2026).
# one-file exe प्रत्येक सुरुवातीला ~40-250 MB temp मध्ये नव्या फोल्डरमध्ये उघडतो आणि Windows Security
# प्रत्येक वेळी सर्व DLL/pyd पुन्हा तपासतो (Smart App Control ने _overlapped.pyd अडवले) - म्हणून सुरुवात संथ.
# इथे सगळं dist/onedir/main/ फोल्डरमध्येच राहतं (main.exe + _internal), UPX नाही. कोड/मार्ग तेच.
# बिल्ड: pyinstaller main_onedir.spec --distpath dist/onedir --workpath build/onedir
# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_submodules

# spec कुठूनही चालवला तरी import path = E-gram फोल्डर (या spec चा फोल्डर). pathex=[] असताना
# C:\Users\User मधून बिल्ड केल्यावर namuna8 वगैरे सापडले नाहीत -> exe मध्ये "No module named 'namuna8'".
EGRAM_DIR = os.path.abspath(SPECPATH)
if EGRAM_DIR not in sys.path:
    sys.path.insert(0, EGRAM_DIR)

# आपले सगळे local packages (काहींना __init__.py नाही - namespace packages) व त्यांचे सगळे submodules.
# main.py auto-register वेळी namuna8/namuna9/certificates चे सगळे submodules import करतो.
LOCAL_PACKAGES = ['namuna8', 'namuna9', 'namuna10', 'certificates', 'ferfar', 'location_management',
                  'reportstab', 'reportRoute', 'LogBook', 'Ghoshawara', 'Yadi', 'JWTapi', 'Utility']
local_hiddenimports = ['database', 'natural_sort']
for _pkg in LOCAL_PACKAGES:
    _mods = collect_submodules(_pkg)
    if not _mods:
        raise SystemExit(f"main_onedir.spec: package '{_pkg}' सापडला नाही ({EGRAM_DIR})")
    local_hiddenimports += _mods

# Utility/QRcodeGeneration.py व print modules qrcode.png <_internal>/reports मध्ये लिहितात (फोल्डर बनवत
# नाहीत) - फोल्डर नसेल तर नमुना-8 print "No such file ... _internal\reports\qrcode.png". रिकामा
# reports फोल्डर (.keep सह, electron-builder रिकामे फोल्डर गाळू नये म्हणून) build मध्ये टाकतो.
_reports_keep = os.path.join(workpath, '_reports_keep')
os.makedirs(_reports_keep, exist_ok=True)
open(os.path.join(_reports_keep, '.keep'), 'w').close()


a = Analysis(
    [os.path.join(EGRAM_DIR, 'main.py')],
    pathex=[EGRAM_DIR],
    binaries=[],
    # uploaded_images (युजरचे फोटो, ~190 MB) व reports (बनवलेले आउटपुट) exe मध्ये टाकत नाही:
    # one-file exe प्रत्येक सुरुवातीला हे सगळं temp मध्ये उघडतो, पण अॅप ते कधीच वापरत नाही -
    # सर्व path exe च्या फोल्डरमधले (cwd) वापरले जातात. त्यामुळे exe लहान व लवकर सुरू होतो.
    datas=[('static', 'static'), ('ReportImages', 'ReportImages'), ('templates', 'templates'),
           (os.path.join(_reports_keep, '.keep'), 'reports')],
    # 'reports' हा code package नाही (बनवलेल्या रिपोर्टचा output फोल्डर) - hidden import नको.
    hiddenimports=['sqlalchemy.ext.declarative'] + local_hiddenimports,
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
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='main',
)
