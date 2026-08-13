#!/usr/bin/env bash
#/ ============================================================================
#/  build_macos.sh — сборка SecretChat.app через PyInstaller (macOS)
#/  build_macos.sh — build SecretChat.app with PyInstaller (macOS)
#/ ============================================================================
#/  результат: dist/SecretChat.app
#/  если раздаёшь приложение — подпиши его, иначе Gatekeeper может ругаться:
#/    codesign --deep --force --sign "Developer ID Application: <Your Name>" dist/SecretChat.app
#/  после подписи: ditto -c -k --keepParent dist/SecretChat.app dist/SecretChat.zip
#/
#/  требования: Python 3.10+, Command Line Tools (xcode-select --install)
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv-build ]; then python3 -m venv .venv-build; fi
.venv-build/bin/python -m pip install --upgrade pip
.venv-build/bin/python -m pip install -r requirements.txt
.venv-build/bin/python -m pip install pyinstaller

.venv-build/bin/python -m PyInstaller --clean --noconfirm secretchat.spec
echo "[OK] done: dist/SecretChat.app"
