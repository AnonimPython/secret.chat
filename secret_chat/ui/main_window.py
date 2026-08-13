#/ ============================================================================
#/  main_window.py — главное окно: сайдбар, вкладки, мост сигналов
#/  main_window.py — main window: sidebar, tabs, the signal bridge
#/ ============================================================================
#/  сетевые потоки не имеют права трогать виджеты, поэтому все события
#/  менеджера прогоняются через мост на Qt-сигналах — это потокобезопасно.
#/  network threads must never touch widgets, so every manager event is
#/  routed through a bridge of Qt signals — that is thread-safe.

from PySide6.QtCore import Qt, QTimer, QObject, Signal
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QListWidget, QListWidgetItem, QStackedWidget,
                               QMessageBox, QFrame, QSizePolicy)

import config as CONFIG
from .. import prefs
from .. import i18n
from ..themes import build_qss
from ..crypto import short_code
from .chat_widget import ChatWidget
from .dialogs import NewChatDialog, JoinDialog, SettingsDialog, IpDialog


#/ ----------------------------------------------------------------------------
#/  мост: сигналы Qt из потоков в GUI-поток
#/  bridge: Qt signals from threads into the GUI thread
#/ ----------------------------------------------------------------------------
class _Bridge(QObject):
  established = Signal(object)
  closed = Signal(object, str)
  message = Signal(object, dict)
  transfer = Signal(object, dict)
  cleared = Signal(object)
  server = Signal(int)
  connect_error = Signal(str, int, str, str)


#/ ----------------------------------------------------------------------------
#/  MainWindow
#/ ----------------------------------------------------------------------------
class MainWindow(QMainWindow):

  def __init__(self, manager):
    super().__init__()
    self.manager = manager
    self.bridge = _Bridge()

    #* коды чатов → строки списка и виджеты       |  chat codes → list rows and widgets
    self._row_by_code = {}
    self._widget_by_code = {}
    self._new_dialog = None
    self._join_dialog = None

    self._build_ui()
    self._wire_events()

    #* секундный тик: таймеры самоуничтожения     |  a one-second tick: self-destruct timers
    self._tick = QTimer(self)
    self._tick.timeout.connect(self._on_tick)
    self._tick.start(1000)

    #* применяем сохранённые тему и язык          |  apply the saved theme and language
    self.apply_theme()
    self.apply_language()


  #/ --- сборка интерфейса ---------------------------------------------------------

  def _build_ui(self):
    self.setWindowTitle(CONFIG.APP_NAME)
    self.resize(CONFIG.WIN_W, CONFIG.WIN_H)
    self.setMinimumSize(CONFIG.WIN_MIN_W, CONFIG.WIN_MIN_H)

    central = QWidget()
    root = QHBoxLayout(central)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)

    #* сайдбар                                     |  the sidebar
    side = QWidget()
    side.setObjectName('sidebar')
    side.setFixedWidth(250)
    side_lay = QVBoxLayout(side)
    side_lay.setContentsMargins(10, 12, 10, 10)
    side_lay.setSpacing(8)

    self.title_label = QLabel(CONFIG.APP_NAME)
    self.title_label.setObjectName('title')
    self.port_label = QLabel()
    self.port_label.setObjectName('hint')

    self.new_btn = QPushButton()
    self.new_btn.setObjectName('accent')
    self.join_btn = QPushButton()

    self.chat_list = QListWidget()
    self.chat_list.setSelectionMode(QListWidget.SingleSelection)

    self.ip_btn = QPushButton()
    self.settings_btn = QPushButton()

    side_lay.addWidget(self.title_label)
    side_lay.addWidget(self.port_label)
    side_lay.addSpacing(4)
    side_lay.addWidget(self.new_btn)
    side_lay.addWidget(self.join_btn)
    side_lay.addSpacing(4)
    side_lay.addWidget(self.chat_list, 1)
    side_lay.addWidget(self.ip_btn)
    side_lay.addWidget(self.settings_btn)

    #* стек вкладок чатов                          |  the chat tab stack
    self.stack = QStackedWidget()

    #* страница-заглушка, когда чатов нет          |  a placeholder page with no chats
    self.placeholder = QWidget()
    ph = QVBoxLayout(self.placeholder)
    ph.addStretch(1)
    self.ph_title = QLabel(CONFIG.APP_NAME)
    self.ph_title.setObjectName('title')
    self.ph_title.setAlignment(Qt.AlignCenter)
    self.ph_hint = QLabel()
    self.ph_hint.setObjectName('hint')
    self.ph_hint.setAlignment(Qt.AlignCenter)
    ph.addWidget(self.ph_title)
    ph.addWidget(self.ph_hint)
    ph.addStretch(1)
    self.stack.addWidget(self.placeholder)

    root.addWidget(side)
    root.addWidget(self.stack, 1)
    self.setCentralWidget(central)

    self.new_btn.clicked.connect(self._open_new)
    self.join_btn.clicked.connect(self._open_join)
    self.ip_btn.clicked.connect(self._open_ip)
    self.settings_btn.clicked.connect(self._open_settings)
    self.chat_list.currentRowChanged.connect(self._switch_chat)


  #/ --- подписки на события менеджера ----------------------------------------------

  def _wire_events(self):
    #* прокидываем события через сигналы моста     |  forward events through the bridge
    self.manager.add_handler('chat_established', lambda chat: self.bridge.established.emit(chat))
    self.manager.add_handler('chat_closed', lambda chat, reason: self.bridge.closed.emit(chat, reason))
    self.manager.add_handler('message_text', lambda chat, msg: self.bridge.message.emit(chat, msg))
    self.manager.add_handler('transfer_done', lambda chat, msg: self.bridge.transfer.emit(chat, msg))
    self.manager.add_handler('chat_cleared', lambda chat: self.bridge.cleared.emit(chat))
    self.manager.add_handler('server_started', lambda port: self.bridge.server.emit(port))
    self.manager.add_handler('connect_error', lambda ip, port, error_key, detail: self.bridge.connect_error.emit(ip, port, error_key, detail))

    #? QueuedConnection: сигнал из чужого потока встанет в очередь GUI-потока
    #? QueuedConnection: a cross-thread signal queues up in the GUI thread
    self.bridge.established.connect(self._on_established, Qt.QueuedConnection)
    self.bridge.closed.connect(self._on_closed, Qt.QueuedConnection)
    self.bridge.message.connect(self._on_message, Qt.QueuedConnection)
    self.bridge.transfer.connect(self._on_transfer, Qt.QueuedConnection)
    self.bridge.cleared.connect(self._on_cleared, Qt.QueuedConnection)
    self.bridge.server.connect(self._on_server, Qt.QueuedConnection)
    self.bridge.connect_error.connect(self._on_connect_error, Qt.QueuedConnection)


  #/ --- слоты моста (run in the GUI thread) -------------------------------------------

  def _on_established(self, chat):
    #* чат появился: строка в списке + вкладка    |  a chat appeared: row + tab
    self._add_chat_row(chat)

    #! диалоги закрываем строго в GUI-потоке — сюда событие приходит уже через мост
    #! dialogs close strictly in the GUI thread — the event already came via the bridge
    if self._new_dialog is not None:
      self._new_dialog.on_established(chat)
    if self._join_dialog is not None:
      self._join_dialog.on_established(chat)

    self._switch_chat(self._row_by_code[chat.code])


  def _on_closed(self, chat, reason):
    #* чат стёрт (выход/таймер/удаление)           |  chat wiped (exit/timer/delete)
    self._remove_chat_row(chat.code)


  def _on_message(self, chat, msg):
    w = self._widget_by_code.get(chat.code)
    if w:
      w.add_message(msg)


  def _on_transfer(self, chat, msg):
    w = self._widget_by_code.get(chat.code)
    if w is None:
      return
    #* чужое вложение — рисуем целиком, своё — обновляем статус
    #* a foreign attachment — render fully, ours — update the status
    if msg.get('mine'):
      w.handle_transfer_done(msg)
    else:
      w.add_message(msg)


  def _on_cleared(self, chat):
    w = self._widget_by_code.get(chat.code)
    if w:
      w.clear_history()


  def _on_server(self, port):
    self.port_label.setText(f"{i18n.tr('listening')} {port}")


  def _on_connect_error(self, ip, port, error_key, detail):
    #* ошибка подключения — показываем в диалоге Join (GUI-поток)
    #* a join error — show it in the Join dialog (GUI thread)
    if self._join_dialog is not None:
      self._join_dialog.on_connect_error(ip, port, error_key, detail)


  #/ --- список чатов -----------------------------------------------------------------

  def _add_chat_row(self, chat):
    code = chat.code
    if code in self._row_by_code:
      return

    item = QListWidgetItem()
    item.setData(Qt.UserRole, code)
    self.chat_list.addItem(item)
    self._row_by_code[code] = self.chat_list.row(item)

    widget = ChatWidget(self.manager, chat)
    self.stack.addWidget(widget)
    self._widget_by_code[code] = widget
    self._refresh_row(chat)


  def _remove_chat_row(self, code):
    row = self._row_by_code.pop(code, None)
    widget = self._widget_by_code.pop(code, None)

    if widget is not None:
      #* убираем вкладку и её данные                |  remove the tab and its data
      self.stack.removeWidget(widget)
      widget.deleteLater()

    if row is not None and self.chat_list.count() > 0:
      #? строка могла уже сдвинуться — ищем по коду |  the row may have shifted — find by code
      for i in range(self.chat_list.count()):
        if self.chat_list.item(i).data(Qt.UserRole) == code:
          self.chat_list.takeItem(i)
          break

      #* пересчитываем индексы после удаления       |  recount indices after the removal
      self._row_by_code = {}
      for i in range(self.chat_list.count()):
        c = self.chat_list.item(i).data(Qt.UserRole)
        self._row_by_code[c] = i

    if self.chat_list.count() == 0:
      self.stack.setCurrentWidget(self.placeholder)


  def _switch_chat(self, row):
    #* переключение вкладки по клику в списке      |  switch the tab on a list click
    if row < 0 or row >= self.chat_list.count():
      return
    code = self.chat_list.item(row).data(Qt.UserRole)
    w = self._widget_by_code.get(code)
    if w:
      self.stack.setCurrentWidget(w)


  #/ --- тик: таймеры самоуничтожения ---------------------------------------------------

  def _on_tick(self):
    #* каждую секунду обновляем счётчики и список  |  every second refresh counters and rows
    for chat in list(self.manager.chats.values()):
      rem = chat.remaining()
      if rem is not None and rem <= 0:
        #! время вышло — чат умирает               |  time is up — the chat dies
        self.manager.destroy_chat(chat.code, reason='timer')
        continue

      self._refresh_row(chat)
      w = self._widget_by_code.get(chat.code)
      if w:
        w.update_timer(rem)


  def _refresh_row(self, chat):
    #* текст строки: адрес собеседника + таймер    |  row text: the peer address + timer
    row = self._row_by_code.get(chat.code)
    if row is None:
      return
    item = self.chat_list.item(row)
    if item is None:
      return

    who = chat.peer_ip or ('…' if chat.state != 'active' else '')
    rem = chat.remaining()
    if rem is None:
      tail = i18n.tr('unlimited')
    else:
      m, s = divmod(int(rem), 60)
      h, m = divmod(m, 60)
      tail = f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    item.setText(f"{who}\n{short_code(chat.code)} · {tail}")


  #/ --- диалоги --------------------------------------------------------------------------

  def _open_new(self):
    #* диалог создателя, модальный                |  the creator dialog, modal
    dlg = NewChatDialog(self.manager, self)
    self._new_dialog = dlg
    #? закрытие диалога идёт через мост в GUI-потоке (см. _on_established)
    #? the dialog closes via the bridge in the GUI thread (see _on_established)
    dlg.exec()
    self._new_dialog = None


  def _open_join(self):
    dlg = JoinDialog(self.manager, self)
    self._join_dialog = dlg
    #? успех и ошибки приходят через мост QueuedConnection — не из сетевого потока
    #? success and errors arrive via the QueuedConnection bridge, not the network thread
    dlg.exec()
    self._join_dialog = None


  def _open_settings(self):
    dlg = SettingsDialog(self.manager, self)
    dlg.apply_initial(
      prefs.effective('theme', CONFIG.THEME),
      prefs.effective('language', CONFIG.LANGUAGE),
      prefs.effective('sound_on', CONFIG.SOUND_ON),
    )
    dlg.exec()


  def _open_ip(self):
    IpDialog(self.manager, self).exec()


  #/ --- тема и язык ------------------------------------------------------------------------

  def apply_theme(self):
    #* перекрашиваем всё приложение одной строкой QSS
    #* repaint the whole app with a single QSS string
    theme = prefs.effective('theme', CONFIG.THEME)
    from PySide6.QtWidgets import QApplication
    QApplication.instance().setStyleSheet(build_qss(theme))


  def apply_language(self):
    #* ставим язык и переписываем подписи          |  set the language and relabel
    lang = prefs.effective('language', CONFIG.LANGUAGE)
    i18n.set_lang(lang)

    self.title_label.setText(CONFIG.APP_NAME)
    self.new_btn.setText(i18n.tr('new_chat'))
    self.join_btn.setText(i18n.tr('join'))
    self.ip_btn.setText(i18n.tr('my_ip'))
    self.settings_btn.setText(i18n.tr('settings'))
    self.port_label.setText(f"{i18n.tr('listening')}: {self.manager.port}")
    self.ph_hint.setText(i18n.tr('create_or_join'))

    #* переводим и вкладки чатов                   |  relabel the chat tabs too
    for w in self._widget_by_code.values():
      w.retranslate()


  #/ --- выход --------------------------------------------------------------------------------

  def closeEvent(self, event):
    #* предупреждаем: всё сотрётся                |  warn: everything will be erased
    answer = QMessageBox.question(self, CONFIG.APP_NAME, i18n.tr('exit_confirm'))
    if answer != QMessageBox.Yes:
      event.ignore()
      return

    #* закрываем сервер и все соединения           |  shut the server and all links
    self.manager.shutdown()
    event.accept()
