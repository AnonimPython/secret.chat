#/ ============================================================================
#/  test_ui_smoke.py — два окна в offscreen-режиме, живой обмен сообщениями
#/  test_ui_smoke.py — two windows in offscreen mode, a live message exchange
#/ ============================================================================
#/  запуск: QT_QPA_PLATFORM=offscreen python tests/test_ui_smoke.py
#/  run:    QT_QPA_PLATFORM=offscreen python tests/test_ui_smoke.py

import os
import sys
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLabel

from secret_chat.manager import ChatManager
from secret_chat.ui import MainWindow
from secret_chat import prefs


def pump(app, secs):
  #* крутим цикл событий, чтобы очереди сигналов разобрались
  #* spin the event loop so the signal queues get processed
  end = time.time() + secs
  while time.time() < end:
    app.processEvents()
    time.sleep(0.02)


def wait_state(mgr, code, want, app, timeout=10):
  #* ждём нужного состояния чата, гоняя события  |  wait for a state while pumping
  end = time.time() + timeout
  while time.time() < end:
    app.processEvents()
    chat = mgr.chats.get(code)
    if chat and chat.state == want:
      return chat
    time.sleep(0.05)
  raise TimeoutError(f'state {want} not reached')


def find_text(widget, text):
  #* есть ли где-то в виджете метка с этим текстом |  is there a label with this text anywhere
  for lab in widget.findChildren(QLabel):
    if lab.text() == text:
      return True
  return False


def main():
  app = QApplication([])

  A = ChatManager(port=43111)
  B = ChatManager(port=43112)
  winA, winB = MainWindow(A), MainWindow(B)
  winA.show(); winB.show()

  #* А создаёт чат, Б подключается                |  A creates, B joins
  code = A.create_chat(0)
  B.join_chat('127.0.0.1', 43111, code)
  wait_state(A, code, 'active', app)
  wait_state(B, code, 'active', app)
  pump(app, 0.5)

  widgetA = winA._widget_by_code[code]
  widgetB = winB._widget_by_code[code]

  #* текст в обе стороны через UI-виджеты         |  text both ways via UI widgets
  A.send_text(code, 'hi from A')
  pump(app, 1.0)
  assert find_text(widgetB, 'hi from A'), 'B must show the message from A'

  widgetB.input.setText('hi back')
  widgetB._on_send()
  pump(app, 1.0)
  assert find_text(widgetA, 'hi back'), 'A must show the message from B'

  #* картинка                                    |  an image
  from PySide6.QtGui import QImage, QColor
  img = QImage(60, 40, QImage.Format_RGB32)
  img.fill(QColor('purple'))
  widgetA.add_image_attachment(img)
  widgetA._on_send()
  pump(app, 2.0)
  assert any(m['kind'] == 'image' for m in B.chats[code].messages), 'B must receive the image'

  #* файл                                        |  a file
  import tempfile
  with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
    f.write(b'x' * 300_000)
    path = f.name
  widgetB.add_file_attachments([path])
  widgetB._on_send()
  pump(app, 3.0)
  assert any(m['kind'] == 'file' for m in A.chats[code].messages), 'A must receive the file'

  #* темы и язык без падений                     |  themes and language without crashes
  prefs.set('theme', 'black'); winA.apply_theme(); pump(app, 0.3)
  prefs.set('theme', 'white'); winA.apply_theme(); pump(app, 0.3)
  prefs.set('language', 'en'); winA.apply_language(); pump(app, 0.3)
  prefs.set('language', 'ru'); winA.apply_language(); pump(app, 0.3)

  #* самоуничтожение по таймеру                  |  self-destruct on the timer
  A.destroy_chat(code, reason='test')
  pump(app, 1.0)
  assert code not in A.chats and code not in B.chats, 'chat must vanish on destroy'

  A.shutdown(); B.shutdown()
  print('UI SMOKE TEST PASSED')


if __name__ == '__main__':
  main()
