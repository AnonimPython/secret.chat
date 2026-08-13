#/ ============================================================================
#/  dialogs.py — создание чата, подключение, настройки, IP
#/  dialogs.py — new chat, join, settings, IP info
#/ ============================================================================
#/  диалоги сами подписываются на события менеджера: так они узнают,
#/  что подключение прошло или сорвалось, и сами себя закрывают.
#/  dialogs subscribe to manager events themselves: that is how they learn
#/  the connection succeeded or failed, and close themselves.

import socket
import threading

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QLineEdit, QComboBox, QSpinBox, QCheckBox, QMessageBox,
                               QFrame)

import config as CONFIG
from ..i18n import tr, theme_name, timer_label
from ..crypto import short_code
from ..themes import PALETTES
from .. import prefs


#/ локальный IP — трюк с UDP: пакеты никуда не уходят, но ОС даёт реальный адрес
#/ LAN IP — the UDP trick: no packets are sent, but the OS returns the real address
def lan_ip():
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    ip = s.getsockname()[0]
    s.close()
    return ip
  except OSError:
    return '127.0.0.1'


#/ разбор строки приглашения «IP:порт:код» в части |  split an "IP:port:code" invite
#/ вернёт (ip, port, code) или None, если это не приглашение
#/ returns (ip, port, code) or None if it is not an invite
def parse_invite(text):
  text = (text or '').strip()
  parts = text.rsplit(':', 2)
  if len(parts) != 3:
    return None
  ip, port_s, code = parts
  try:
    port = int(port_s)
  except ValueError:
    return None
  if not (1 <= port <= 65535) or not ip.strip() or not code.strip():
    return None
  return ip.strip(), port, code.strip()


#/ ----------------------------------------------------------------------------
#/  NewChatDialog — создатель: выбрал таймер, получил код, ждёт собеседника
#/  NewChatDialog — creator: picked a timer, got the code, waits for the peer
#/ ----------------------------------------------------------------------------
class NewChatDialog(QDialog):

  def __init__(self, manager, parent=None):
    super().__init__(parent)
    self.manager = manager
    self.code = None
    self.invite = None
    self._pending_timer = False
    self.setMinimumWidth(430)
    self._build_ui()
    self.retranslate()
    self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)


  def _build_ui(self):
    lay = QVBoxLayout(self)
    lay.setSpacing(10)

    self.title = QLabel()
    self.title.setObjectName('title')

    #* выбор времени жизни чата                   |  the chat lifetime picker
    self.timer_label = QLabel()
    self.timer_combo = QComboBox()
    for minutes in CONFIG.DESTROY_PRESETS:
      self.timer_combo.addItem(timer_label(minutes), minutes)

    self.create_btn = QPushButton()
    self.create_btn.setObjectName('accent')

    #* блок кода, появляется после создания       |  the code block, appears after creation
    self.code_label = QLabel()
    self.code_label.setObjectName('title')
    self.code_label.setWordWrap(True)
    self.code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    self.code_label.setAlignment(Qt.AlignCenter)
    #? высоту задаём min-height, а не паддингом: паддинг 22+22 обрезал текст
    #? height via min-height, not padding: 22+22 padding clipped the text away
    self.code_label.setMinimumHeight(64)
    #? цвета явные (инлайн не наследует QSS в тёмном режиме macOS — текст был невидим)
    #? explicit colors (inline styles don't inherit QSS in macOS dark mode — text was invisible)
    pal = PALETTES.get(prefs.effective('theme', CONFIG.THEME), PALETTES['black'])
    self.code_label.setStyleSheet(
      f'font-family: monospace; font-size: 15px; color: {pal["text"]}; '
      f'background-color: {pal["input"]}; padding: 14px 16px; '
      f'border: 1px dashed {pal["border"]}; border-radius: 8px;')
    self.code_label.hide()

    self.copy_btn = QPushButton()
    self.copy_btn.setObjectName('accent')
    self.copy_btn.hide()

    self.hint = QLabel()
    self.hint.setObjectName('hint')
    self.hint.setWordWrap(True)

    lay.addWidget(self.title)
    lay.addWidget(self.timer_label)
    lay.addWidget(self.timer_combo)
    lay.addWidget(self.create_btn)
    lay.addWidget(self.code_label)
    lay.addWidget(self.copy_btn)
    lay.addWidget(self.hint)

    self.create_btn.clicked.connect(self._create)
    self.copy_btn.clicked.connect(self._copy)
    self.setFixedWidth(460)


  def retranslate(self):
    #* текст диалога на текущем языке             |  the dialog text in the current language
    self.title.setText(tr('new_chat'))
    self.timer_label.setText(tr('timer_question'))
    self.create_btn.setText(tr('create_chat'))
    self.copy_btn.setText(tr('copy_invite'))


  def _create(self):
    #* создаём чат и показываем приглашение        |  create the chat and show the invite
    minutes = self.timer_combo.currentData()
    self.code = self.manager.create_chat(minutes)

    #? в одной строке сразу IP:порт:код — копируй и отправляй целиком
    #? a single IP:port:code line — copy and send it as is
    self.invite = f'{lan_ip()}:{self.manager.port}:{self.code}'

    self.timer_label.hide()
    self.timer_combo.hide()
    self.create_btn.hide()

    self.code_label.setText(self.invite)
    self.code_label.show()
    self.copy_btn.show()
    self.hint.setText(tr('waiting') + '\n' + tr('invite_hint'))
    self._pending_timer = True


  def _copy(self):
    #* приглашение в буфер обмена                 |  the invite into the clipboard
    from PySide6.QtWidgets import QApplication
    QApplication.clipboard().setText(self.invite or self.code or '')
    self.copy_btn.setText(tr('copied'))
    #? возвращаем подпись обратно через полсекунды |  revert the label after half a second
    from PySide6.QtCore import QTimer
    QTimer.singleShot(700, lambda: self.copy_btn.setText(tr('copy_invite')))


  def on_established(self, chat):
    #* собеседник пришёл — закрываемся            |  the peer arrived — close us
    if chat.code == self.code:
      self._pending_timer = False
      self.accept()


  def closeEvent(self, event):
    #* закрыли диалог до подключения — отменяем чат |  closed before connecting — cancel the chat
    if self._pending_timer and self.code:
      self.manager.cancel_pending(self.code)
    super().closeEvent(event)


#/ ----------------------------------------------------------------------------
#/  JoinDialog — подключающийся: IP + порт + код
#/  JoinDialog — the joiner: IP + port + code
#/ ----------------------------------------------------------------------------
class JoinDialog(QDialog):

  def __init__(self, manager, parent=None):
    super().__init__(parent)
    self.manager = manager
    self._joining = False
    self._want_code = None
    self.setMinimumWidth(430)
    self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
    self._build_ui()
    self.retranslate()


  def _build_ui(self):
    lay = QVBoxLayout(self)
    lay.setSpacing(10)

    self.title = QLabel()
    self.title.setObjectName('title')

    self.ip_label = QLabel()
    self.ip_edit = QLineEdit()
    self.ip_edit.setPlaceholderText('192.168.1.42')

    self.port_label = QLabel()
    self.port_spin = QSpinBox()
    self.port_spin.setRange(1, 65535)
    self.port_spin.setValue(CONFIG.PORT)

    self.code_label = QLabel()
    self.code_edit = QLineEdit()
    self.code_edit.setPlaceholderText('XXXX-XXXX-…')

    self.join_btn = QPushButton()
    self.join_btn.setObjectName('accent')

    self.status = QLabel()
    self.status.setObjectName('hint')
    self.status.setWordWrap(True)

    row_port = QHBoxLayout()
    row_port.addWidget(self.port_label)
    row_port.addWidget(self.port_spin, 1)

    lay.addWidget(self.title)
    lay.addWidget(self.ip_label)
    lay.addWidget(self.ip_edit)
    lay.addLayout(row_port)
    lay.addWidget(self.code_label)
    lay.addWidget(self.code_edit)
    lay.addWidget(self.join_btn)
    lay.addWidget(self.status)

    self.join_btn.clicked.connect(self._join)
    #? если вставили целое приглашение — разберём его на IP/порт/код
    #? if a whole invite was pasted — split it into IP/port/code
    self.code_edit.textChanged.connect(self._maybe_parse_invite)
    self.setFixedWidth(460)


  def retranslate(self):
    self.title.setText(tr('join_chat'))
    self.ip_label.setText(tr('ip'))
    self.port_label.setText(tr('port'))
    self.code_label.setText(tr('code'))
    self.join_btn.setText(tr('join'))
    self.status.setText(tr('connecting_hint'))
    self.code_edit.setPlaceholderText(tr('code_or_invite_placeholder'))


  def _maybe_parse_invite(self, text):
    #* если в поле кода лежит готовое приглашение — заполняем IP и порт сами
    #* if the code field holds a ready invite — fill IP and port ourselves
    parsed = parse_invite(text)
    if not parsed:
      return
    ip, port, code = parsed
    self.ip_edit.setText(ip)
    self.port_spin.setValue(port)
    #? заменяем приглашение на чистый код, не входя в рекурсию
    #? replace the invite with the bare code without recursing
    self.code_edit.blockSignals(True)
    self.code_edit.setText(code)
    self.code_edit.blockSignals(False)
    self.status.setText(tr('invite_parsed'))


  def _join(self):
    #* шлём запрос подключения, кнопку глушим     |  fire the join, mute the button
    #? если в поле кода всё ещё целое приглашение — разберём его
    #? if the code field still holds a whole invite — split it
    parsed = parse_invite(self.code_edit.text())
    if parsed:
      ip, port, code = parsed
      self.ip_edit.setText(ip)
      self.port_spin.setValue(port)
      self.code_edit.setText(code)

    ip = self.ip_edit.text().strip()
    code = self.code_edit.text().strip().upper()

    if not ip or not code:
      self.status.setText(tr('conn_failed'))
      return

    self._want_code = code
    self._joining = True
    self.join_btn.setEnabled(False)
    self.status.setText(tr('connecting'))
    self.manager.join_chat(ip, self.port_spin.value(), code)


  def on_connect_error(self, ip, port, error_key, detail):
    #* что-то пошло не так — показываем по-человечески
    #* something failed — show it in plain terms
    if not self._joining:
      return
    self._joining = False
    self.join_btn.setEnabled(True)

    #? ключи ошибок переводятся тут, чтобы ядро не знало про язык
    #? error keys are translated here so the core never knows about language
    msg = tr('err_bad_code') if error_key == 'bad_code' else \
          tr('err_timeout') if error_key == 'timeout' else \
          tr('err_refused') if error_key == 'refused' else \
          tr('err_wrong_peer') if error_key == 'wrong_peer' else tr('err_unknown')
    if detail:
      msg += f'\n{detail}'
    self.status.setText(msg)


  def on_established(self, chat):
    #* всё сошлось — закрываемся                  |  everything matched — close us
    if self._joining:
      self.accept()


#/ ----------------------------------------------------------------------------
#/  SettingsDialog — тема, язык, звук, порт
#/  SettingsDialog — theme, language, sound, port
#/ ----------------------------------------------------------------------------
class SettingsDialog(QDialog):

  def __init__(self, manager, parent=None):
    super().__init__(parent)
    self.manager = manager
    self.setMinimumWidth(360)
    self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
    self._build_ui()
    self.retranslate()


  def _build_ui(self):
    lay = QVBoxLayout(self)
    lay.setSpacing(12)

    self.title = QLabel()
    self.title.setObjectName('title')

    self.theme_label = QLabel()
    self.theme_combo = QComboBox()
    #* список тем из конфига, имена локализованы   |  themes from the config, localized names
    for tid in CONFIG.THEMES:
      self.theme_combo.addItem(theme_name(tid), tid)

    self.lang_label = QLabel()
    self.lang_combo = QComboBox()
    self.lang_combo.addItem('Русский', 'ru')
    self.lang_combo.addItem('English', 'en')

    self.sound_label = QLabel()
    self.sound_check = QCheckBox()

    self.port_label = QLabel()
    self.port_spin = QSpinBox()
    self.port_spin.setRange(1024, 65535)
    self.port_spin.setValue(self.manager.port)

    self.status = QLabel()
    self.status.setObjectName('hint')

    self.close_btn = QPushButton()
    self.close_btn.setObjectName('accent')

    self.wipe_btn = QPushButton()
    self.wipe_btn.setObjectName('danger')

    def _row(label, widget):
      #* строчка «подпись : поле»                  |  a "label : field" row
      r = QHBoxLayout()
      r.addWidget(label)
      r.addWidget(widget, 1)
      return r

    lay.addWidget(self.title)
    lay.addLayout(_row(self.theme_label, self.theme_combo))
    lay.addLayout(_row(self.lang_label, self.lang_combo))
    lay.addLayout(_row(self.sound_label, self.sound_check))
    lay.addLayout(_row(self.port_label, self.port_spin))
    lay.addWidget(self.status)
    lay.addWidget(self.close_btn)
    lay.addWidget(self.wipe_btn)

    self.theme_combo.currentIndexChanged.connect(self._apply)
    self.lang_combo.currentIndexChanged.connect(self._apply)
    self.sound_check.toggled.connect(self._apply)
    self.port_spin.valueChanged.connect(self._apply)
    self.close_btn.clicked.connect(self.accept)
    self.wipe_btn.clicked.connect(self._wipe)


  def _wipe(self):
    #* «Удалить все данные»: подтверждаем и чистим диск от принятых файлов
    #* "delete all data": confirm and clear the disk of received files
    if QMessageBox.question(self, tr('delete_all'), tr('delete_all_confirm')) != QMessageBox.Yes:
      return
    if self.manager.wipe_disk_data():
      QMessageBox.information(self, tr('ok'), tr('deleted_all'))
    else:
      QMessageBox.warning(self, tr('error'), tr('save_failed'))


  def retranslate(self):
    self.title.setText(tr('settings'))
    self.theme_label.setText(tr('theme'))
    self.lang_label.setText(tr('language'))
    self.sound_label.setText(tr('sound'))
    self.close_btn.setText(tr('save'))
    self.wipe_btn.setText(tr('delete_all'))


  def apply_initial(self, theme, lang, sound):
    #* выставить текущие значения без лишних сигналов |  set current values without extra signals
    i = self.theme_combo.findData(theme)
    if i >= 0: self.theme_combo.setCurrentIndex(i)
    j = self.lang_combo.findData(lang)
    if j >= 0: self.lang_combo.setCurrentIndex(j)
    self.sound_check.setChecked(sound)


  def _apply(self):
    #* применяем всё на лету и сохраняем в prefs  |  apply everything live and save to prefs
    from .. import prefs

    theme = self.theme_combo.currentData()
    lang = self.lang_combo.currentData()
    sound = self.sound_check.isChecked()
    port = self.port_spin.value()

    prefs.set('theme', theme)
    prefs.set('language', lang)
    prefs.set('sound_on', sound)
    prefs.set('port', port)

    #* просим окно перерисовать стиль и язык      |  ask the window to restyle and relabel
    if self.parent():
      self.parent().apply_theme()
      self.parent().apply_language()

    #* порт сменили — сервер перезапускаем        |  the port changed — restart the server
    if port != self.manager.port:
      self.manager.port = port
      self.manager.start_server()


#/ ----------------------------------------------------------------------------
#/  IpDialog — свои адреса: локальный, внешний, подсказка про NAT
#/  IpDialog — own addresses: LAN, public, and a NAT hint
#/ ----------------------------------------------------------------------------
class IpDialog(QDialog):

  def __init__(self, manager, parent=None):
    super().__init__(parent)
    self.manager = manager
    self.setMinimumWidth(360)
    self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
    self._build_ui()
    self.retranslate()


  def _build_ui(self):
    lay = QVBoxLayout(self)
    lay.setSpacing(10)

    self.title = QLabel()
    self.title.setObjectName('title')

    self.lan_label = QLabel()
    self.lan_label.setObjectName('title')
    self.lan_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

    self.port_label = QLabel()
    self.port_label.setObjectName('hint')

    self.ext_btn = QPushButton()
    self.ext_label = QLabel()
    self.ext_label.setObjectName('hint')
    self.ext_label.setWordWrap(True)

    self.note = QLabel()
    self.note.setObjectName('hint')
    self.note.setWordWrap(True)

    self.close_btn = QPushButton()
    self.close_btn.setObjectName('accent')

    lay.addWidget(self.title)
    lay.addWidget(self.lan_label)
    lay.addWidget(self.port_label)
    lay.addWidget(self.ext_btn)
    lay.addWidget(self.ext_label)
    lay.addWidget(self.note)
    lay.addWidget(self.close_btn)

    self.ext_btn.clicked.connect(self._check_public)
    self.close_btn.clicked.connect(self.accept)
    self.setFixedWidth(420)


  def retranslate(self):
    self.title.setText(tr('my_ip'))
    self.ext_btn.setText(tr('external_ip'))
    self.close_btn.setText(tr('save'))
    self.note.setText(tr('nat_hint'))
    #* локальный IP считаем при каждом открытии   |  compute the LAN IP on every open
    self.lan_label.setText(f"{tr('lan_ip')}: {lan_ip()}")
    self.port_label.setText(f"{tr('listening')}: {self.manager.port}")


  def _lan_ip(self):
    return lan_ip()


  def _check_public(self):
    #* внешний IP — спрашиваем STUN-сервер в потоке, чтобы не висеть
    #* public IP — ask a STUN server in a thread so we never freeze
    self.ext_btn.setEnabled(False)
    self.ext_label.setText(tr('waiting'))

    def work():
      ip = self._stun()
      from PySide6.QtCore import QMetaObject, Qt as _Qt, Q_ARG
      QMetaObject.invokeMethod(self, 'ext_result', _Qt.QueuedConnection, Q_ARG(str, ip or ''))

    threading.Thread(target=work, daemon=True).start()


  def _stun(self):
    #* минимальный STUN binding-запрос (без данных о пользователе)
    #* a minimal STUN binding request (no user data)
    try:
      import struct
      from ..crypto import secrets
      sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      sock.settimeout(4)
      #* 20 байт заголовка + атрибут USERNAME пустой — классика RFC 5389
      #* 20-byte header + empty USERNAME attr — classic RFC 5389
      txid = secrets.token_bytes(12)
      req = struct.pack('>HHI', 0x0001, 0, 0x2112A442) + txid
      sock.sendto(req, ('stun.l.google.com', 19302))
      data, _ = sock.recvfrom(2048)
      sock.close()
      #* ищем XOR-MAPPED-ADDRESS и достаём IP     |  find XOR-MAPPED-ADDRESS and read the IP
      magic = 0x2112A442
      if len(data) < 24:
        return None
      msg_type, length = struct.unpack('>HH', data[:4])
      if msg_type != 0x0101:
        return None
      i = 20
      end = 20 + min(length, len(data) - 20)
      while i + 4 <= end:
        atype, alen = struct.unpack('>HH', data[i:i + 4])
        if atype == 0x0020 and alen >= 8:
          fam = data[i + 4 + 1]
          if fam == 0x01:
            xport = struct.unpack('>H', data[i + 6:i + 8])[0]
            port = xport ^ (magic >> 16)
            xaddr = struct.unpack('>I', data[i + 8:i + 12])[0]
            addr = socket.inet_ntoa(struct.pack('>I', xaddr ^ magic))
            return f'{addr}:{port}'
        i += 4 + alen
        #? атрибуты выравниваются по 4 байта       |  attributes align to 4 bytes
        if alen % 4:
          i += 4 - (alen % 4)
      return None
    except Exception:
      return None


  def ext_result(self, ip):
    #* возврат из потока: показать или честно сказать, что не вышло
    #* thread return: show it or honestly say it failed
    self.ext_btn.setEnabled(True)
    if ip:
      self.ext_label.setText(f"{tr('external_ip')}: {ip}")
    else:
      self.ext_label.setText(tr('err_timeout'))
