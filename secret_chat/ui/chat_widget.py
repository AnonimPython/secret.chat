#/ ============================================================================
#/  chat_widget.py — окно одного чата: шапка, лента сообщений, ввод
#/  chat_widget.py — one chat window: header, message stream, input
#/ ============================================================================
#/  сюда не лезут сетевые потоки: виджет только рисует и шлёт команды
#/  менеджеру. события менеджера приходят через сигналы из main_window.
#/  network threads never touch this widget: it only draws and commands the
#/  manager. manager events arrive via signals from main_window.

import os
import time

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon, QImage, QTextCursor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                               QPushButton, QTextEdit, QScrollArea, QFileDialog,
                               QApplication, QSizePolicy)

import config as CONFIG
from ..i18n import tr, theme_name
from ..themes import PALETTES
from .. import prefs, sound


#/ ----------------------------------------------------------------------------
#/  PasteEdit — поле ввода с вставкой фото и файлов
#/  PasteEdit — the input box with image/file paste support
#/ ----------------------------------------------------------------------------
class PasteEdit(QTextEdit):

  #* сигналы наружу: вставили фото / файлы / нажали отправить
  #* signals outwards: pasted photo / files / pressed send
  image_pasted = Signal(object)
  files_pasted = Signal(list)
  send_pressed = Signal()


  def __init__(self):
    super().__init__()
    #? rich text не нужен — чат текстовый        |  no rich text — the chat is plain text
    self.setAcceptRichText(False)
    #? перенос строк как в мессенджерах          |  line breaks like in messengers
    self.setLineWrapMode(QTextEdit.WidgetWidth)
    #* компактное поле ввода                      |  a compact input field
    self.setMinimumHeight(40)
    self.setMaximumHeight(120)


  def canInsertFromMimeData(self, mime):
    #* картинки и файлы — можно, это наше         |  images and files — sure, that's ours
    return mime.hasImage() or mime.hasUrls()


  def insertFromMimeData(self, mime):
    #* вставка фото (Ctrl+V с картинкой)          |  paste an image (Ctrl+V with a picture)
    if mime.hasImage():
      img = QImage(mime.imageData())
      if not img.isNull():
        self.image_pasted.emit(img)
      return

    #* вставка файлов из проводника               |  paste files from the file manager
    if mime.hasUrls():
      paths = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
      paths = [p for p in paths if os.path.isfile(p)]
      if paths:
        self.files_pasted.emit(paths)
        return

    #* текст — как обычно                         |  text — as usual
    super().insertFromMimeData(mime)


  def keyPressEvent(self, event):
    #* Enter (без Shift) — отправить; Shift+Enter — перенос строки
    #* plain Enter sends; Shift+Enter inserts a new line
    if event.key() in (Qt.Key_Return, Qt.Key_Enter):
      if event.modifiers() & Qt.ShiftModifier:
        super().keyPressEvent(event)
      else:
        self.send_pressed.emit()
      event.accept()
      return
    super().keyPressEvent(event)


#/ ----------------------------------------------------------------------------
#/  ChatWidget — весь чат целиком
#/  ChatWidget — the whole chat
#/ ----------------------------------------------------------------------------
class ChatWidget(QWidget):

  def __init__(self, manager, chat, parent=None):
    super().__init__(parent)
    #* помним код чата и менеджера                |  remember the chat code and the manager
    self.manager = manager
    self.chat = chat
    self.code = chat.code
    self.attachments = []
    self._bubbles = {}
    self._build_ui()
    self.retranslate()


  #/ --- сборка интерфейса (build UI) -------------------------------------------

  def _build_ui(self):
    root = QVBoxLayout(self)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)

    root.addWidget(self._build_header())
    root.addWidget(self._build_scroll(), 1)
    root.addWidget(self._build_attachments_row())
    root.addLayout(self._build_input_row())


  def _build_header(self):
    #* шапка: кто напротив + таймер + кнопки      |  header: who is across + timer + buttons
    bar = QWidget()
    bar.setObjectName('header')

    lay = QHBoxLayout(bar)
    lay.setContentsMargins(12, 8, 12, 8)

    self.peer_label = QLabel()
    self.peer_label.setObjectName('title')
    self.code_label = QLabel()
    self.code_label.setObjectName('hint')

    left = QVBoxLayout()
    left.setSpacing(1)
    left.addWidget(self.peer_label)
    left.addWidget(self.code_label)

    self.timer_label = QLabel()
    self.timer_label.setObjectName('hint')
    self.timer_label.setAlignment(Qt.AlignCenter)
    self.timer_label.setMinimumWidth(140)

    self.clear_btn = QPushButton()
    self.delete_btn = QPushButton()
    self.delete_btn.setObjectName('danger')

    lay.addLayout(left)
    lay.addStretch(1)
    lay.addWidget(self.timer_label)
    lay.addWidget(self.clear_btn)
    lay.addWidget(self.delete_btn)

    self.clear_btn.clicked.connect(self._on_clear)
    self.delete_btn.clicked.connect(self._on_delete)
    return bar


  def _build_scroll(self):
    #* лента сообщений с автоскроллом             |  message stream with auto-scroll
    self.scroll = QScrollArea()
    self.scroll.setWidgetResizable(True)
    self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    self.stream = QWidget()
    self.stream.setObjectName('stream')
    self.stream_layout = QVBoxLayout(self.stream)
    self.stream_layout.setContentsMargins(10, 10, 10, 10)
    self.stream_layout.setSpacing(6)
    #* пружина внизу держит пузыри сверху         |  a bottom spring keeps bubbles on top
    self.stream_layout.addStretch(1)

    self.scroll.setWidget(self.stream)
    return self.scroll


  def _build_attachments_row(self):
    #* ряд превью вложений, прячется если пусто   |  preview row, hidden when empty
    self.att_row = QFrame()
    self.att_row.setObjectName('att_row')
    self.att_lay = QHBoxLayout(self.att_row)
    self.att_lay.setContentsMargins(8, 6, 8, 6)
    self.att_lay.setSpacing(6)
    self.att_lay.addStretch(1)
    self.att_row.hide()
    return self.att_row


  def _build_input_row(self):
    row = QHBoxLayout()
    row.setContentsMargins(8, 8, 8, 8)
    row.setSpacing(8)

    self.attach_btn = QPushButton()
    self.attach_btn.setObjectName('attach_btn')
    self.attach_btn.setCursor(Qt.PointingHandCursor)
    self.attach_btn.setFixedSize(38, 38)
    self.input = PasteEdit()
    self.send_btn = QPushButton()
    self.send_btn.setObjectName('send_btn')
    self.send_btn.setCursor(Qt.PointingHandCursor)
    self.send_btn.setFixedSize(38, 38)

    self.attach_btn.clicked.connect(self._pick_file)
    self.send_btn.clicked.connect(self._on_send)
    self.input.image_pasted.connect(self.add_image_attachment)
    self.input.files_pasted.connect(self.add_file_attachments)
    self.input.send_pressed.connect(self._on_send)

    row.addWidget(self.attach_btn)
    row.addWidget(self.input, 1)
    row.addWidget(self.send_btn)
    return row


  #/ --- пересборка текстов при смене языка (retranslate) ------------------------

  def retranslate(self):
    #* обновляем все статичные подписи            |  refresh every static label
    ip = self.chat.peer_ip or tr('waiting')
    self.peer_label.setText(f"{tr('peer')}: {ip}")
    self.code_label.setText(f"{tr('code')}: {self.code[:19]}…")

    self.attach_btn.setText('+')
    self.attach_btn.setToolTip(tr('attach'))
    self.input.setPlaceholderText(tr('msg_placeholder'))
    self.send_btn.setText('➤')
    self.send_btn.setToolTip(tr('send'))
    self.clear_btn.setText(tr('clear'))
    self.delete_btn.setText(tr('delete'))


  #/ --- входящие события (incoming events) ---------------------------------------

  def add_message(self, msg):
    #* рисуем сообщение и, если чужое, пищим      |  draw a message; beep if it's foreign
    if not msg.get('mine'):
      sound.play_incoming()
    self._append_bubble(msg)
    #? скроллим после раскладки, иначе лента может не доехать до конца
    #? scroll after layout, otherwise the stream may not reach the bottom
    from PySide6.QtCore import QTimer
    QTimer.singleShot(0, self._scroll_bottom)


  def handle_transfer_done(self, data):
    #* отправка/приём завершены — обновляем статус |  transfer finished — update the status
    mid = data.get('id')
    bubble = self._bubbles.get(mid)
    if bubble is None:
      return
    status = bubble.get('status')
    if status is not None:
      status.setText(tr('sent') if data.get('mine') else tr('sent'))


  def clear_history(self):
    #* убираем все пузыри, оставляя пружину        |  drop all bubbles, keep the spring
    self._bubbles.clear()
    while self.stream_layout.count() > 1:
      item = self.stream_layout.takeAt(0)
      w = item.widget()
      if w:
        w.deleteLater()


  #/ --- вложения (attachments) ----------------------------------------------------

  def add_image_attachment(self, image):
    #* из буфера: кладём в превью и в память      |  from clipboard: to the preview and RAM
    if len(self.attachments) >= CONFIG.MAX_ATTACHMENTS:
      return
    #* PySide6 не умеет QImage в BytesIO — идём через QBuffer
    #* PySide6 can't do QImage into BytesIO — go through QBuffer
    from PySide6.QtCore import QBuffer, QByteArray
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QBuffer.WriteOnly)
    image.save(buf, 'PNG')
    buf.close()
    name = self._photo_name()
    self.attachments.append({'type': 'image', 'name': name, 'data': bytes(ba), 'pix': QPixmap.fromImage(image)})
    self._refresh_attachments()


  def add_file_attachments(self, paths):
    #* файлы с диска                              |  files from disk
    for p in paths:
      if len(self.attachments) >= CONFIG.MAX_ATTACHMENTS:
        break
      self.attachments.append({'type': 'file', 'name': os.path.basename(p), 'path': p, 'data': None})
    self._refresh_attachments()


  def _refresh_attachments(self):
    #* перерисовываем ряд превью                  |  redraw the preview row
    while self.att_lay.count() > 1:
      item = self.att_lay.takeAt(0)
      w = item.widget()
      if w:
        w.deleteLater()

    for i, att in enumerate(self.attachments):
      chip = self._att_chip(att, i)
      self.att_lay.insertWidget(self.att_lay.count() - 1, chip)

    self.att_row.setVisible(bool(self.attachments))


  def _att_chip(self, att, index):
    #* маленькая карточка вложения с крестиком    |  a small attachment card with an X
    chip = QFrame()
    chip.setObjectName('att_row')
    h = QHBoxLayout(chip)
    h.setContentsMargins(6, 4, 6, 4)
    h.setSpacing(4)

    if att['type'] == 'image':
      thumb = QLabel()
      thumb.setPixmap(att['pix'].scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
      h.addWidget(thumb)
    else:
      icon = QLabel()
      icon.setText('[' + tr('file') + ']')
      h.addWidget(icon)

    name = QLabel(att['name'][:18])
    name.setObjectName('hint')
    h.addWidget(name)

    rm = QPushButton('x')
    rm.setFixedSize(22, 22)
    rm.setStyleSheet('padding:0;')
    rm.clicked.connect(lambda _, i=index: self._remove_attachment(i))
    h.addWidget(rm)
    return chip


  def _remove_attachment(self, index):
    #* убрать вложение из очереди отправки        |  drop an attachment from the queue
    if 0 <= index < len(self.attachments):
      self.attachments.pop(index)
    self._refresh_attachments()


  def _pick_file(self):
    #* выбор файла диалогом                       |  pick a file via the dialog
    paths, _ = QFileDialog.getOpenFileNames(self, tr('attach'))
    if paths:
      self.add_file_attachments(paths)


  #/ --- отправка (sending) ----------------------------------------------------------

  def _on_send(self):
    #* читаем текст, шлём текст и вложения        |  read the text, send text and attachments
    text = self.input.toPlainText().strip()

    if not text and not self.attachments:
      return

    if self.chat.state != 'active':
      return

    if text:
      self.manager.send_text(self.code, text)

    for att in list(self.attachments):
      if att['type'] == 'image':
        self.manager.send_image(self.code, att['name'], att['data'])
      else:
        self.manager.send_file(self.code, att['path'])

    self.attachments.clear()
    self._refresh_attachments()
    self.input.clear()


  def _on_clear(self):
    #* очистка истории у обоих                   |  clear history on both sides
    self.manager.clear_chat(self.code)
    self.clear_history()


  def _on_delete(self):
    #* удаление чата у обоих, с подтверждением    |  delete the chat on both sides, confirmed
    from PySide6.QtWidgets import QMessageBox
    if QMessageBox.question(self, tr('delete'), tr('delete_confirm')) == QMessageBox.Yes:
      self.manager.destroy_chat(self.code, reason='deleted')


  #/ --- пузыри сообщений (bubbles) ---------------------------------------------------

  def _append_bubble(self, msg):
    #* строим виджет и кладём в ленту             |  build a widget and drop it in
    bubble = self._make_bubble(msg)
    self._bubbles[msg['id']] = bubble

    #? вставляем перед пружиной (последний индекс) |  insert before the spring (last index)
    idx = self.stream_layout.count() - 1
    self.stream_layout.insertWidget(idx, bubble['frame'])


  def _make_bubble(self, msg):
    #* внешняя рамка: своя справа, чужая слева    |  outer frame: mine right, theirs left
    mine = bool(msg.get('mine'))
    pal = PALETTES.get(prefs.effective('theme', CONFIG.THEME), PALETTES['black'])

    frame = QFrame()
    frame.setMaximumWidth(CONFIG.BUBBLE_MAX_WIDTH + 24)

    #* цвета берём инлайн-стилем прямо из палитры, чтобы каскад QSS
    #* не ломался и на светлых темах текст оставался читаемым
    #* colors come inline straight from the palette so the QSS cascade
    #* can't break text readability on light themes
    if mine:
      radius = '16px 16px 5px 16px'
      bg = (f'qlineargradient(x1:0, y1:0, x2:1, y2:1, '
            f'stop:0 {pal["me"]}, stop:1 {self._shade(pal["me"], -16)})')
      fg, meta, card_bg = '#ffffff', 'rgba(255,255,255,0.82)', 'rgba(255,255,255,0.14)'
    else:
      radius = '16px 16px 16px 5px'
      bg = pal['them']
      fg, meta, card_bg = pal['text'], pal['dim'], 'rgba(0,0,0,0.05)'

    frame.setStyleSheet(
      f'QFrame {{ background: {bg}; border-radius: {radius}; }}')

    inner = QVBoxLayout(frame)
    inner.setContentsMargins(12, 10, 12, 8)
    inner.setSpacing(3)

    if msg['kind'] == 'text':
      label = QLabel(msg['text'])
      label.setWordWrap(True)
      label.setTextInteractionFlags(Qt.TextSelectableByMouse)
      label.setStyleSheet(f'color: {fg}; font-size: 14px;')
      inner.addWidget(label)

    elif msg['kind'] == 'image':
      inner.addWidget(self._image_label(msg))
      if not mine:
        #* под фото — явная кнопка «Сохранить»      |  an explicit Save button under the photo
        btn = QPushButton(tr('save'))
        btn.setObjectName('accent')
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda _c=False, m=msg: self._save_file(m))
        btn.setFixedWidth(110)
        inner.addWidget(btn, alignment=Qt.AlignLeft)

    elif msg['kind'] == 'file':
      inner.addWidget(self._file_card(msg, fg, meta, card_bg))

    #* футер: время + статус/размер                |  footer: time + status/size
    foot = QHBoxLayout()
    foot.setSpacing(8)
    foot.addStretch(1)

    ts = msg.get('ts') or time.time()
    tsl = QLabel(time.strftime('%H:%M', time.localtime(ts)))
    tsl.setStyleSheet(f'color: {meta}; font-size: 10px;')
    foot.addWidget(tsl)

    status = None
    if msg.get('status') in ('sending', 'sent'):
      status = QLabel(tr('sending') if msg.get('status') == 'sending' else tr('sent'))
      status.setStyleSheet(f'color: {meta}; font-size: 11px;')
      foot.addWidget(status)
    elif msg.get('size') and msg['kind'] in ('image', 'file'):
      status = QLabel(self._human_size(msg.get('size', 0)))
      status.setStyleSheet(f'color: {meta}; font-size: 11px;')
      foot.addWidget(status)
    inner.addLayout(foot)

    #* выравнивание контейнера                      |  the container alignment
    row = QWidget()
    row_lay = QHBoxLayout(row)
    row_lay.setContentsMargins(0, 0, 0, 0)
    if mine:
      row_lay.addStretch(1)
    row_lay.addWidget(frame)
    if not mine:
      row_lay.addStretch(1)

    return {'frame': row, 'status': status}


  def _image_label(self, msg):
    #* картинка внутри пузыря, клик = сохранить     |  image inside a bubble, click = save
    pix = QPixmap()
    if msg.get('data'):
      pix.loadFromData(msg['data'])
    else:
      pix.load(msg.get('path', ''))

    if pix.isNull():
      return QLabel('[?]')

    if pix.width() > CONFIG.IMAGE_MAX_WIDTH:
      pix = pix.scaledToWidth(CONFIG.IMAGE_MAX_WIDTH, Qt.SmoothTransformation)

    label = QLabel()
    label.setPixmap(pix)
    label.setCursor(Qt.PointingHandCursor)
    label.setToolTip(tr('save'))
    label.mousePressEvent = lambda _e, m=msg: self._save_image(m)
    return label


  def _file_card(self, msg, fg, meta, card_bg):
    #* карточка файла с кнопкой «Открыть»          |  a file card with an "Open" button
    card = QFrame()
    card.setStyleSheet(f'QFrame {{ background: {card_bg}; border-radius: 10px; }}')
    lay = QVBoxLayout(card)
    lay.setContentsMargins(10, 8, 10, 8)

    name = QLabel(msg.get('name', '?'))
    name.setWordWrap(True)
    name.setTextInteractionFlags(Qt.TextSelectableByMouse)
    name.setStyleSheet(f'color: {fg}; font-size: 13px; font-weight: 600;')
    lay.addWidget(name)

    size = QLabel(self._human_size(msg.get('size', 0)))
    size.setStyleSheet(f'color: {meta}; font-size: 11px;')
    lay.addWidget(size)

    if not msg.get('mine'):
      row = QHBoxLayout()
      row.setSpacing(6)
      row.addStretch(1)
      for label, slot in ((tr('open'), self._open_file), (tr('save'), self._save_file)):
        btn = QPushButton(label)
        btn.setObjectName('accent')
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda _c=False, m=msg, s=slot: s(m))
        row.addWidget(btn)
      lay.addLayout(row)

    return card


  def _save_file(self, msg):
    #* сохранить принятый файл в выбранное место   |  save a received file somewhere chosen
    data = msg.get('data')
    path = msg.get('path')
    if not data and not (path and os.path.isfile(path)):
      return
    default = os.path.join(CONFIG.SAVE_DIR, msg.get('name', 'file'))
    out, _ = QFileDialog.getSaveFileName(self, tr('save'), default)
    if not out:
      return
    try:
      if data is not None:
        with open(out, 'wb') as f:
          f.write(data)
      else:
        import shutil
        shutil.copyfile(path, out)
    except OSError as exc:
      from PySide6.QtWidgets import QMessageBox
      QMessageBox.warning(self, tr('error'), f"{tr('save_failed')}:\n{exc}")
      return
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.information(self, tr('ok'), tr('saved'))


  def _save_image(self, msg):
    #* сохранить картинку в выбранное место        |  save the image somewhere chosen
    from PySide6.QtWidgets import QMessageBox
    data = msg.get('data')
    if not data:
      return
    path, _ = QFileDialog.getSaveFileName(self, tr('save'), msg.get('name', 'image.png'))
    if path:
      with open(path, 'wb') as f:
        f.write(data)
      QMessageBox.information(self, tr('ok'), tr('saved'))


  def _open_file(self, msg):
    #* открыть принятый файл системным способом    |  open the received file the system way
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtCore import QUrl
    path = msg.get('path')
    if not (path and os.path.isfile(path)):
      #* файл в памяти — материализуем во временный файл, чтобы ОС смогла его открыть
      #* a RAM-only file — materialize it so the OS can open it
      path = self._materialize(msg)
    if path and os.path.isfile(path):
      QDesktopServices.openUrl(QUrl.fromLocalFile(path))


  def _materialize(self, msg):
    #* временная копия файла из памяти (в /tmp, чистит сама система)
    #* a temp copy of a RAM file (in /tmp, cleaned by the OS itself)
    data = msg.get('data')
    if not data:
      return None
    try:
      os.makedirs(CONFIG.TMP_DIR, exist_ok=True)
      path = os.path.join(CONFIG.TMP_DIR, 'open_' + (msg.get('name') or 'file'))
      with open(path, 'wb') as f:
        f.write(data)
      return path
    except OSError:
      return None


  #/ --- служебное (helpers) -----------------------------------------------------------

  @staticmethod
  def _shade(color, amount):
    #* осветлить (+)/затемнить (−) hex-цвет в процентах |  lighten (+)/darken (−) a hex color in percent
    color = color.lstrip('#')
    if len(color) != 6:
      return f'#{color}'
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    f = 1.0 + amount / 100.0
    return f'#{int(max(0, min(255, r * f))):02x}{int(max(0, min(255, g * f))):02x}{int(max(0, min(255, b * f))):02x}'

  def _photo_name(self):
    #* имя вставленного фото по времени            |  name the pasted photo by time
    import time as _t
    return _t.strftime('photo_%Y%m%d_%H%M%S.png')


  def _human_size(self, n):
    #* красивые единицы размера                    |  nice size units
    for unit in ('B', 'KB', 'MB', 'GB'):
      if n < 1024:
        return f'{int(n)} {unit}'
      n /= 1024
    return f'{n:.1f} TB'


  def _scroll_bottom(self):
    #* после нового сообщения едем вниз            |  after a new message scroll down
    sb = self.scroll.verticalScrollBar()
    sb.setValue(sb.maximum())


  def update_timer(self, remaining):
    #* обновить счётчик самоуничтожения            |  refresh the self-destruct counter
    if remaining is None:
      self.timer_label.setText(tr('unlimited'))
    else:
      m, s = divmod(int(remaining), 60)
      h, m = divmod(m, 60)
      text = f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
      self.timer_label.setText(f"{tr('destroy_in')} {text}")
