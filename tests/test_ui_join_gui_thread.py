#/ ============================================================================
#/  test_ui_join_gui_thread.py — диалоги закрываются только в GUI-потоке
#/  test_ui_join_gui_thread.py — dialogs close only in the GUI thread
#/ ============================================================================
#/  баг: события менеджера зовут обработчики в том потоке, который их сгенерил
#/  (сетевой поток). Если там же вызывается dlg.accept()/setText() — Qt пишет
#/  «Cannot filter events for objects in a different thread» и приложение
#/  зависает у пользователя.
#/  тест по-настоящему соединяет два окна и проверяет, что on_established и
#/  on_connect_error диалогов вызываются строго в GUI-потоке.
#/
#/  bug: manager events call handlers in whichever thread produced them (the
#/  network thread). Calling dlg.accept()/setText() there makes Qt print
#/  "Cannot filter events for objects in a different thread" and hang on the
#/  user's machine.
#/  this test really connects two windows and asserts that the dialogs'
#/  on_established and on_connect_error run strictly in the GUI thread.
#/
#/  цикл крутим через processEvents, а не exec(): на offscreen-платформе
#/  app.quit() из таймера не выходит из exec(), когда показано окно.
#/  we pump the loop with processEvents instead of exec(): on the offscreen
#/  platform app.quit() from a timer never leaves exec() while a window is up.
#/
#/  запуск: QT_QPA_PLATFORM=offscreen .venv/bin/python tests/test_ui_join_gui_thread.py
#/  run:     QT_QPA_PLATFORM=offscreen .venv/bin/python tests/test_ui_join_gui_thread.py

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from secret_chat.manager import ChatManager
from secret_chat.ui.main_window import MainWindow
from secret_chat.ui.dialogs import NewChatDialog, JoinDialog


def pump(app, until, timeout=15):
  #* крутим событийный цикл, пока предикат не станет истинным |  pump until the predicate is true
  end = time.time() + timeout
  while time.time() < end:
    app.processEvents()
    if until():
      return True
    time.sleep(0.02)
  return False


def main():
  app = QApplication(sys.argv)
  app.setQuitOnLastWindowClosed(False)
  gui_thread = app.thread()

  #* подмена: фиксируем, из какого потока зовётся каждый метод диалога
  #* monkeypatch: record which thread calls each dialog method
  calls = {'established': [], 'connect_error': []}
  _orig_est, _orig_err = JoinDialog.on_established, JoinDialog.on_connect_error

  def _est(self, chat):
    calls['established'].append(QThread.currentThread())
    return _orig_est(self, chat)

  def _err(self, ip, port, error_key, detail):
    calls['connect_error'].append(QThread.currentThread())
    return _orig_err(self, ip, port, error_key, detail)

  JoinDialog.on_established, JoinDialog.on_connect_error = _est, _err

  #* два настоящих приложения на разных портах    |  two real apps on distinct ports
  mgr_a = ChatManager(port=43271)
  mgr_a.start_server()
  mgr_b = ChatManager(port=43272)
  mgr_b.start_server()

  win_a = MainWindow(mgr_a)
  win_b = MainWindow(mgr_b)
  win_a.show()
  win_b.show()

  #* та же схема, что в _open_new/_open_join       |  the same wiring as in _open_new/_open_join
  dlg_new = NewChatDialog(mgr_a, win_a)
  win_a._new_dialog = dlg_new
  dlg_join = JoinDialog(mgr_b, win_b)
  win_b._join_dialog = dlg_join

  code = mgr_a.create_chat(0)
  dlg_new.code = code
  dlg_join.ip_edit.setText('127.0.0.1')
  dlg_join.port_spin.setValue(mgr_a.port)
  dlg_join.code_edit.setText(code)
  dlg_join._join()

  def joined_ok():
    active_a = any(c.state == 'active' for c in mgr_a.chats.values())
    active_b = any(c.state == 'active' for c in mgr_b.chats.values())
    return active_a and active_b and dlg_join.result() != 0 and dlg_new.result() != 0

  if not pump(app, joined_ok):
    print('FAIL: connection never completed on the GUI thread')
    sys.exit(1)

  #* вторая часть: путь ошибки подключения        |  part two: the connect-error path
  dlg_join2 = JoinDialog(mgr_b, win_b)
  win_b._join_dialog = dlg_join2
  dlg_join2.ip_edit.setText('127.0.0.1')
  dlg_join2.port_spin.setValue(43999)   #! пустой порт — будет refused
  dlg_join2.code_edit.setText('AAAA-BBBB-CCCC-DDDD-EEEE')
  dlg_join2._join()

  def error_shown():
    return bool(dlg_join2.status.text())

  if not pump(app, error_shown):
    print('FAIL: connect-error never reached the dialog')
    sys.exit(1)

  mgr_a.shutdown()
  mgr_b.shutdown()

  ok = calls['established'] and all(t is gui_thread for t in calls['established'])
  ok = ok and calls['connect_error'] and all(t is gui_thread for t in calls['connect_error'])
  if not ok:
    print('FAIL: dialog methods were called from a non-GUI thread')
    print('  established threads:', [t is gui_thread for t in calls['established']])
    print('  connect_error threads:', [t is gui_thread for t in calls['connect_error']])
    sys.exit(1)

  print('GUI-THREAD TEST PASSED')


if __name__ == '__main__':
  main()
