#!/usr/bin/env bash
#/ ============================================================================
#/  build_linux.sh — сборка SecretChat через PyInstaller (Linux)
#/  build_linux.sh — build SecretChat with PyInstaller (Linux)
#/ ============================================================================
#/  результат: dist/SecretChat  (один исполняемый файл)
#/
#/  требования:
#/    • python3, python3-venv, pip
#/    • системные библиотеки Qt (Debian/Ubuntu):
#/        sudo apt install build-essential libgl1 libegl1 libxkbcommon0
#/    • в headless-окружении добавь к запуску: QT_QPA_PLATFORM=offscreen
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv-build ]; then python3 -m venv .venv-build; fi
.venv-build/bin/python -m pip install --upgrade pip
.venv-build/bin/python -m pip install -r requirements.txt
.venv-build/bin/python -m pip install pyinstaller

.venv-build/bin/python -m PyInstaller --clean --noconfirm secretchat.spec
echo "[OK] done: dist/SecretChat"
