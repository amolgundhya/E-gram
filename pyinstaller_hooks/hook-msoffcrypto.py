# Overrides pyinstaller-hooks-contrib's hook-msoffcrypto.py, which copies the
# pip metadata of "msoffcrypto-tool". msoffcrypto is vendored in ./msoffcrypto
# (no pip metadata; only its CLI --version reads it), so collect the package
# modules instead.
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('msoffcrypto')
