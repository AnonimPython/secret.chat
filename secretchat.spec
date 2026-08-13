# -*- mode: python ; coding: utf-8 -*-
#/ ============================================================================
#/  secretchat.spec — PyInstaller-сборка SecretChat (.exe / .app)
#/  secretchat.spec — PyInstaller build of SecretChat (.exe / .app)
#/ ============================================================================
#/  одна спецификация на обе ОС (запасной вариант; основная сборка — Nuitka,
#/  см. build/build_windows_nuitka.bat — он меньше триггерит антивирусы):
#/  one spec for both OSes (a fallback; the main build is Nuitka,
#/  see build/build_windows_nuitka.bat — it triggers fewer AV flags):

import sys

#? скрытые импорты — QtMultimedia и cryptography часто теряются при упаковке
#? hidden imports — QtMultimedia and cryptography are often lost during packing
hiddenimports = [
  'cryptography.hazmat.primitives.asymmetric.x25519',
  'cryptography.hazmat.primitives.ciphers.aead',
  'cryptography.hazmat.primitives.kdf.hkdf',
  'PySide6.QtMultimedia',
]

a = Analysis(
  ['main.py'],
  pathex=['.'],
  binaries=[],
  datas=[('assets', 'assets')],
  hiddenimports=hiddenimports,
  hookspath=[],
  runtime_hooks=[],
  excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'tkinter'],
  noarchive=False,
)

pyz = PYZ(a.pure)

# -----------------------------------------------------------------------------
#  macOS: bundle (.app)  |  macOS: a proper .app bundle
# -----------------------------------------------------------------------------
if sys.platform == 'darwin':
  exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SecretChat',
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
  )

  coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='SecretChat')

  app = BUNDLE(
    coll,
    name='SecretChat.app',
    icon='assets/logo.icns',
    bundle_identifier='com.secretchat.app',
    info_plist={
      'NSHighResolutionCapable': True,
      'LSMinimumSystemVersion': '11.0',
      'CFBundleShortVersionString': '1.0.0',
      'CFBundleVersion': '1.0.0',
    },
  )

# -----------------------------------------------------------------------------
#  Windows: onefile .exe  |  Windows: a single .exe
# -----------------------------------------------------------------------------
else:
  exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SecretChat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # без консольного окна  |  no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.ico',
  )
