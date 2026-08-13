
'''
 ▗▄▖ ▗▖  ▗▖ ▗▄▖ ▗▖  ▗▖▗▄▄▄▖▗▖  ▗▖▗▄▄▖ ▗▖  ▗▖▗▄▄▄▖▗▖ ▗▖ ▗▄▖ ▗▖  ▗▖
▐▌ ▐▌▐▛▚▖▐▌▐▌ ▐▌▐▛▚▖▐▌  █  ▐▛▚▞▜▌▐▌ ▐▌ ▝▚▞▘   █  ▐▌ ▐▌▐▌ ▐▌▐▛▚▖▐▌
▐▛▀▜▌▐▌ ▝▜▌▐▌ ▐▌▐▌ ▝▜▌  █  ▐▌  ▐▌▐▛▀▘   ▐▌    █  ▐▛▀▜▌▐▌ ▐▌▐▌ ▝▜▌
▐▌ ▐▌▐▌  ▐▌▝▚▄▞▘▐▌  ▐▌▗▄█▄▖▐▌  ▐▌▐▌     ▐▌    █  ▐▌ ▐▌▝▚▄▞▘▐▌  ▐▌
'''


#!/usr/bin/env python3
#/ ============================================================================
#/  main.py — точка входа приложения SecretChat
#/  main.py — the SecretChat application entry point
#/ ============================================================================
#/  запуск:  python main.py            (нужен виртуальный дисплей для GUI)
#/  run:      python main.py            (a display is needed for the GUI)
#/  в контейнере GUI поднимается на Xvfb и доступен через noVNC — см. docker/
#/  in a container the GUI runs on Xvfb and is reachable via noVNC — see docker/

import os
import sys

#/ корень проекта в sys.path — чтобы работало «import config» из любого места
#/ put the project root on sys.path so "import config" works from anywhere
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon

import config as CONFIG
from secret_chat import prefs
from secret_chat.manager import ChatManager
from secret_chat.ui import MainWindow


def resource_path(rel):
  #* путь к ресурсам: исходники vs упакованный exe/app (_MEIPASS)
  #* resources path: source tree vs a frozen exe/app (_MEIPASS)
  base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
  return os.path.join(base, rel)


def main():
  #* порт: конфиг → runtime-перекрытие            |  port: config → runtime override
  port = prefs.effective('port', CONFIG.PORT)
  if not isinstance(port, int) or not (1 <= port <= 65535):
    port = CONFIG.PORT

  app = QApplication(sys.argv)
  app.setApplicationName(CONFIG.APP_NAME)
  app.setApplicationVersion(CONFIG.APP_VERSION)

  #* иконка приложения: окно и панель задач (Win), док (macOS)
  #* app icon: window and taskbar (Win), dock (macOS)
  icon_name = 'logo.icns' if sys.platform == 'darwin' else 'logo.ico'
  app.setWindowIcon(QIcon(resource_path(os.path.join('assets', icon_name))))

  #* системный шрифт чуть крупнее — читается лучше |  a slightly larger system font
  font = app.font()
  font.setPointSize(prefs.effective('font_size', CONFIG.FONT_SIZE))
  app.setFont(font)

  #* ядро (сеть, шифрование, чаты)                 |  the core (network, crypto, chats)
  manager = ChatManager(port=port)

  window = MainWindow(manager)
  window.show()

  #! при выходе приложение само закроет все соединения и чаты
  #! on exit the app shuts every connection and chat on its own
  code = app.exec()
  manager.shutdown()
  sys.exit(code)


if __name__ == '__main__':
  main()
