# Folder (one-dir) build - main.spec ची प्रत, फक्त पॅकिंग बदलले (Nov-2026).
# one-file exe प्रत्येक सुरुवातीला ~40-250 MB temp मध्ये नव्या फोल्डरमध्ये उघडतो आणि Windows Security
# प्रत्येक वेळी सर्व DLL/pyd पुन्हा तपासतो (Smart App Control ने _overlapped.pyd अडवले) - म्हणून सुरुवात संथ.
# इथे सगळं dist/onedir/main/ फोल्डरमध्येच राहतं (main.exe + _internal), UPX नाही. कोड/मार्ग तेच.
# बिल्ड: pyinstaller main_onedir.spec --distpath dist/onedir --workpath build/onedir
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # uploaded_images (युजरचे फोटो, ~190 MB) व reports (बनवलेले आउटपुट) exe मध्ये टाकत नाही:
    # one-file exe प्रत्येक सुरुवातीला हे सगळं temp मध्ये उघडतो, पण अॅप ते कधीच वापरत नाही -
    # सर्व path exe च्या फोल्डरमधले (cwd) वापरले जातात. त्यामुळे exe लहान व लवकर सुरू होतो.
    datas=[('static', 'static'), ('ReportImages', 'ReportImages'), ('templates', 'templates')],
        hiddenimports=['sqlalchemy.ext.declarative', 'namuna8', 'namuna9', 'namuna10', 'certificates', 'ferfar', 'location_management', 'reports', 'reportstab', 'LogBook', 'Ghoshawara', 'Yadi', 'JWTapi', 'Utility'] + collect_submodules('namuna8') + collect_submodules('namuna9') + collect_submodules('certificates'),
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
