#!/usr/bin/env python3
#/ ============================================================================
#/  make_icons.py — генерирует assets/logo.ico и assets/logo.icns из логотипа
#/  make_icons.py — generates assets/logo.ico and assets/logo.icns from the logo
#/ ============================================================================
#/  использование (usage):  .venv-build/bin/python build/make_icons.py
#/  требует (needs):       Pillow, iconutil (macOS)
#/  результат (output):
#/    assets/logo.ico    — Windows: exe-иконка + иконка окна (16..256 px)
#/    assets/logo.icns   — macOS:   иконка .app в Dock и в Finder
#/
#/  базовый логотип: screenshots/chat/logo.jpg  |  source logo: screenshots/chat/logo.jpg

import os
import shutil
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'screenshots', 'chat', 'logo.jpg')
OUT = os.path.join(ROOT, 'assets')
ICONSET = os.path.join(OUT, 'logo.iconset')

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
ICONSET_SIZES = [16, 16, 32, 32, 128, 128, 256, 256, 512, 512]  # @1x, @2x pairs
ICONSET_FILES = [
    'icon_16x16.png', 'icon_16x16@2x.png',
    'icon_32x32.png', 'icon_32x32@2x.png',
    'icon_128x128.png', 'icon_128x128@2x.png',
    'icon_256x256.png', 'icon_256x256@2x.png',
    'icon_512x512.png', 'icon_512x512@2x.png',
]


def main():
    if not os.path.exists(SRC):
        sys.exit(f'[!] no logo at {SRC}')

    img = Image.open(SRC).convert('RGBA')

    os.makedirs(OUT, exist_ok=True)

    #* .ico — набор размеров в одном файле  |  a single .ico with many sizes
    img.save(os.path.join(OUT, 'logo.ico'), format='ICO', sizes=[(s, s) for s in ICO_SIZES])
    print('[OK] assets/logo.ico', ICO_SIZES)

    #* .icns — через iconset + iconutil  |  .icns via iconset + iconutil
    if os.path.exists(ICONSET):
        shutil.rmtree(ICONSET)
    os.makedirs(ICONSET)
    for size, name in zip(ICONSET_SIZES, ICONSET_FILES):
        img.resize((size, size), Image.LANCZOS).save(os.path.join(ICONSET, name))
    subprocess.run(['iconutil', '-c', 'icns', ICONSET, '-o',
                    os.path.join(OUT, 'logo.icns')], check=True)
    shutil.rmtree(ICONSET)
    print('[OK] assets/logo.icns')

    print('[DONE] icons are ready in assets/')


if __name__ == '__main__':
    main()
