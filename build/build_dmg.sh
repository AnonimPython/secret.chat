#!/usr/bin/env bash
#/ ============================================================================
#/  build_dmg.sh — упаковка dist/SecretChat.app в дистрибутив SecretChat.dmg
#/  build_dmg.sh — pack dist/SecretChat.app into a SecretChat.dmg installer
#/ ============================================================================
#/  сперва собери .app: ./build/build_macos.sh
#/  сначала нужен .app:  ./build/build_macos.sh
set -euo pipefail
cd "$(dirname "$0")/.."

APP=dist/SecretChat.app
STAGE=dist/dmg_stage
DMG=dist/SecretChat.dmg

if [ ! -d "$APP" ]; then
  echo "[!] no $APP — run ./build/build_macos.sh first"
  exit 1
fi

rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

rm -f "$DMG"
hdiutil create -volname "SecretChat" -srcfolder "$STAGE" -ov -format UDZO "$DMG"

rm -rf "$STAGE"
echo "[OK] done: $DMG"
