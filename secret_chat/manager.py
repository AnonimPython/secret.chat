#/ ============================================================================
#/  manager.py — ядро: чаты, рукопожатие, шифрование, самоуничтожение
#/  manager.py — the core: chats, handshake, encryption, self-destruct
#/ ============================================================================
#/  менеджер ничего не знает про Qt. Он только считает и стучится в события.
#/  UI подписывается на события и сам решает, что показать.
#/  the manager knows nothing about Qt. It just computes and fires events.
#/  the UI subscribes to events and decides what to show.

import base64
import hashlib
import json
import os
import shutil
import tempfile
import threading
import time

import config as CONFIG
from . import crypto
from . import network
from . import protocol


#/ состояния чата  |  chat states
CHAT_PENDING = 'pending'
CHAT_ACTIVE  = 'active'
CHAT_CLOSED  = 'closed'


#/ ----------------------------------------------------------------------------
#/  Chat — состояние одного разговора
#/  Chat — the state of one conversation
#/ ----------------------------------------------------------------------------
class Chat:

  #* обычный набор полей, без магии             | plain field set, no magic
  def __init__(self, code, creator, my_private, my_public, destroy_min):
    self.code = code
    self.creator = creator
    self.my_private = my_private
    self.my_public = my_public
    self.peer_public = None
    self.aes_key = None
    self.destroy_min = destroy_min
    self.created_ts = time.time()
    self.expiry_ts = None
    self.peer_ip = None
    self.state = CHAT_PENDING
    self.conn = None
    self.messages = []
    self.transfers_in = {}
    self._msg_lock = threading.Lock()

  #* сколько секунд осталось до самоуничтожения | seconds left until self-destruct
  def remaining(self):
    if self.expiry_ts is None: return None
    return max(0.0, self.expiry_ts - time.time())


#/ ----------------------------------------------------------------------------
#/  ChatManager — вся логика
#/  ChatManager — all the logic
#/ ----------------------------------------------------------------------------
class ChatManager:

  #* поднимаем сервер сразу, порт из конфига    | start the server right away, port from config
  def __init__(self, port=None):
    self.port = port or CONFIG.PORT
    self.chats = {}
    self._lock = threading.Lock()
    self._handlers = {}
    self.server = None
    self._stopping = False
    #? проверка таймеров в фоне — надёжнее, чем полагаться на UI
    #? background timer check — more reliable than relying on the UI
    self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True, name='timer')
    self._timer_thread.start()
    if CONFIG.START_SERVER:
      self.start_server()


  #/ --- события (events) ------------------------------------------------------

  def add_handler(self, event, fn):
    #* подписка не стирает других — обработчиков может быть сколько угодно
    #* subscribing never overwrites others — any number of handlers is fine
    self._handlers.setdefault(event, []).append(fn)

  def emit(self, event, **kw):
    #* зовём все обработчики из потока, который вызвал emit
    #* call every handler from whichever thread called emit
    for fn in self._handlers.get(event, []):
      try: fn(**kw)
      except Exception:
        pass


  #/ --- сервер (server) --------------------------------------------------------

  def start_server(self):
    #* если старый сервер жив — сначала гасим    | kill an old server first
    if self.server: self.server.stop()

    server = network.NetworkServer(self, self.port)
    result = server.start()

    if isinstance(result, int):
      self.server = server
      self.port = result
      self.emit('server_started', port=result)

    else:
      #! порт занят? пробуем следующую пару вариантов, потом сдаёмся
      #! port busy? try a couple of neighbouring ones, then give up
      for offset in (1, 2, 3):
        server = network.NetworkServer(self, self.port + offset * CONFIG.PORT_RETRY_OFFSET)
        result = server.start()
        if isinstance(result, int):
          self.server = server
          self.port = result
          self.emit('server_started', port=result)
          return

      self.emit('server_failed', error=str(result))


  def stop_server(self):
    #* выключаем сервер, соединения остаются    | stop the server, keep connections
    if self.server:
      self.server.stop()
      self.server = None


  #/ --- создание и подключение (create & join) ---------------------------------

  def create_chat(self, destroy_min):
    #* создатель: генерим пару ключей и код      | creator: generate a keypair and a code
    private, public = crypto.generate_keypair()
    code = crypto.generate_pairing_code(public)

    with self._lock:
      chat = Chat(code, creator=True, my_private=private, my_public=public, destroy_min=destroy_min)
      self.chats[code] = chat

    self.emit('log', level='INFO', text=f'chat created {code[:11]}…')
    return code


  def cancel_pending(self, code):
    #* создатель передумал ждать — убираем чат  | creator stopped waiting — drop the chat
    with self._lock:
      chat = self.chats.pop(code, None)
    if chat and chat.conn:
      chat.conn.close()


  def join_chat(self, ip, port, code):
    #* подключаемся в фоне, чтобы UI не завис    | connect in a thread so the UI never freezes
    threading.Thread(target=self._join_worker, args=(ip, port, code), daemon=True, name='join').start()


  def _join_worker(self, ip, port, code):
    #! код сломан (опечатка/проверка) — скажем сразу
    #! broken code (typo / checksum) — say it right away
    try:
      creator_public = crypto.parse_pairing_code(code)
    except ValueError as exc:
      self.emit('connect_error', ip=ip, port=port, error_key='bad_code', detail=str(exc))
      return

    #* своя пара ключей для этого чата           | our own keypair for this chat
    private, public = crypto.generate_keypair()

    try:
      sock = network.connect_to(ip, port)
      #? таймаут на чтение рукопожатия, чтобы не висеть вечно
      #? read timeout for the handshake so we never hang forever
      sock.settimeout(CONFIG.HANDSHAKE_READ_TIMEOUT)

      #* шлём: версию, код и свой публичный ключ  | send version, code and our public key
      init = {'v': CONFIG.APP_VERSION, 'code': code, 'pub': base64.b64encode(public).decode('ascii')}
      protocol.write_frame(sock, protocol.FT_HS_INIT, base64.b64encode(json.dumps(init).encode('utf-8')))

      ftype, payload = protocol.read_frame(sock)

      if ftype == protocol.FT_HS_ERR:
        #! сервер отклонил — покажем его причину  | the server rejected — show its reason
        err = base64.b64decode(payload).decode('utf-8', 'replace')
        sock.close()
        self.emit('connect_error', ip=ip, port=port, error_key='rejected', detail=err)
        return

      if ftype != protocol.FT_HS_RESP:
        sock.close()
        self.emit('connect_error', ip=ip, port=port, error_key='unknown', detail='no handshake reply')
        return

      resp = json.loads(base64.b64decode(payload).decode('utf-8'))

      #! публичный ключ из ответа обязан совпасть с тем, что зашит в код
      #! the public key in the reply MUST match the one baked into the code
      resp_pub = base64.b64decode(resp['peer_pub'])
      if resp_pub != creator_public:
        sock.close()
        self.emit('connect_error', ip=ip, port=port, error_key='wrong_peer', detail='key mismatch')
        return

      #* общий секрет ECDH → ключ AES            | ECDH shared secret → AES key
      shared = crypto.compute_shared_secret(private, resp_pub)
      aes_key = crypto.derive_aes_key(shared, code)

      destroy_min = int(resp.get('destroy_min', 0))

      with self._lock:
        chat = Chat(code, creator=False, my_private=private, my_public=public, destroy_min=destroy_min)
        chat.peer_public = resp_pub
        chat.aes_key = aes_key
        chat.peer_ip = ip
        chat.state = CHAT_ACTIVE
        if destroy_min > 0:
          #* таймер стартует с момента рукопожатия | the timer starts at the handshake
          chat.expiry_ts = chat.created_ts + destroy_min * 60
        self.chats[code] = chat

      #* оборачиваем сокет и включаем потоки      | wrap the socket and start the threads
      self._attach_conn(chat, sock)

      self.emit('log', level='INFO', text=f'joined chat {ip}:{port}')
      self.emit('chat_established', chat=chat)

    except socket.timeout as exc:
      self._safe_close(sock)
      self.emit('connect_error', ip=ip, port=port, error_key='timeout', detail=str(exc))

    except ConnectionRefusedError:
      self._safe_close(sock)
      self.emit('connect_error', ip=ip, port=port, error_key='refused', detail='connection refused')

    except Exception as exc:
      self._safe_close(sock)
      self.emit('connect_error', ip=ip, port=port, error_key='unknown', detail=str(exc))


  #/ --- входящие соединения (incoming) ------------------------------------------

  def handle_inbound(self, conn, addr):
    #* принимаем только рукопожатие, дальше — ChatConnection
    #* accept only the handshake, then it's a ChatConnection
    try:
      conn.settimeout(CONFIG.HANDSHAKE_READ_TIMEOUT)
      ftype, payload = protocol.read_frame(conn)

      if ftype != protocol.FT_HS_INIT:
        self._hs_error(conn, 'not a handshake')
        return

      init = json.loads(base64.b64decode(payload).decode('utf-8'))
      code = init.get('code', '')
      peer_pub = base64.b64decode(init.get('pub', ''))

      with self._lock:
        chat = self.chats.get(code)

      #! чата с таким кодом нет или он уже активен
      #! no chat with this code, or it is already active
      if chat is None:
        self._hs_error(conn, 'code not found')
        return
      if chat.state == CHAT_ACTIVE:
        self._hs_error(conn, 'already connected')
        return
      if chat.state == CHAT_CLOSED:
        self._hs_error(conn, 'chat closed')
        return

      #* создатель: ECDH со своим приватным ключом  | creator: ECDH with its own private key
      shared = crypto.compute_shared_secret(chat.my_private, peer_pub)
      aes_key = crypto.derive_aes_key(shared, code)

      #* отвечаем своим публичным ключом и таймером  | reply with our public key and the timer
      resp = {'ok': True, 'peer_pub': base64.b64encode(chat.my_public).decode('ascii'), 'destroy_min': chat.destroy_min}
      protocol.write_frame(conn, protocol.FT_HS_RESP, base64.b64encode(json.dumps(resp).encode('utf-8')))

      with self._lock:
        chat.peer_public = peer_pub
        chat.aes_key = aes_key
        chat.peer_ip = addr[0]
        chat.state = CHAT_ACTIVE
        if chat.destroy_min > 0 and chat.expiry_ts is None:
          chat.expiry_ts = chat.created_ts + chat.destroy_min * 60

      #* сокет из accept уже наш — просто оборачиваем
      #* the accepted socket is already ours — just wrap it
      self._attach_conn(chat, conn)

      self.emit('log', level='INFO', text=f'incoming connected from {addr[0]}')
      self.emit('chat_established', chat=chat)

    except Exception as exc:
      #! что-то пошло не так на рукопожатии — молча закрываем
      #! something went wrong during the handshake — close quietly
      self.emit('log', level='WARN', text=f'handshake error: {exc}')
      try: conn.close()
      except OSError: pass


  #* короткий ответ с ошибкой рукопожатия        | short handshake error reply
  def _hs_error(self, conn, reason):
    try:
      payload = base64.b64encode(reason.encode('utf-8'))
      protocol.write_frame(conn, protocol.FT_HS_ERR, payload)
    except OSError:
      pass
    try: conn.close()
    except OSError: pass


  def _attach_conn(self, chat, sock):
    #* колбэки привязываем к конкретному чату      | bind callbacks to a specific chat
    def on_json(obj): self._on_json(chat, obj)
    def on_blob(mid, idx, total, data): self._on_blob(chat, mid, idx, total, data)
    def on_dead(): self._on_dead(chat)

    conn = network.ChatConnection(sock, chat.aes_key, on_json, on_blob, on_dead)
    chat.conn = conn
    conn.start()

    #* вежливое hello, чтобы другая сторона поняла, что ключи сошлись
    #* a polite hello so the other side knows the keys matched
    conn.send_json({'t': 'hello', 'v': CONFIG.APP_VERSION})


  #* собеседник отключился или умер              | the peer disconnected or died
  def _on_dead(self, chat):
    if chat.state == CHAT_CLOSED: return
    self.emit('log', level='INFO', text=f'chat {chat.code[:8]} link lost')
    #! чат стирается: кто-то вышел — стираем у обоих
    #! the chat is erased: someone left — erased on both sides
    self._destroy_local(chat, reason='disconnect')


  #/ --- события от соединения (connection events) --------------------------------

  def _on_json(self, chat, obj):
    #* диспетчер по типам сообщений                | dispatch by message type
    t = obj.get('t')

    if t == 'ping':
      #? пинг на пинг не отвечаем — нечего плодить трафик
      #? no ping-for-ping — don't waste traffic
      return

    if t == 'hello':
      return

    if t == 'text':
      msg = {'id': obj['id'], 'kind': 'text', 'mine': False, 'text': obj['text'], 'ts': time.time()}
      with chat._msg_lock: chat.messages.append(msg)
      self.emit('message_text', chat=chat, msg=msg)

    elif t == 'file_meta':
      #* начинаем приём файла, держим путь и хэш   | start receiving, keep path and hash
      mid = obj['id']
      size = int(obj['size'])
      limit = CONFIG.MAX_FILE_MB * 1024 * 1024
      if limit and size > limit:
        chat.conn.send_json({'t': 'file_cancel', 'id': mid, 'reason': 'too_large'})
        return

      os.makedirs(CONFIG.TMP_DIR, exist_ok=True)
      tmp = tempfile.NamedTemporaryFile(delete=False, dir=CONFIG.TMP_DIR, prefix='recv_', suffix='.part')
      chat.transfers_in[mid] = {
        'meta': obj, 'tmp': tmp, 'path': tmp.name, 'received': 0,
        'sha': hashlib.sha256(), 'total_chunks': None,
      }

    elif t == 'file_done':
      #* пришли итоговые метаданные — сохраняем хэш | final metadata arrived — keep the hash
      tr = chat.transfers_in.get(obj['id'])
      if tr is not None:
        tr['meta']['sha256'] = obj.get('sha256', '')
        tr['meta']['size'] = int(obj.get('size', tr['meta'].get('size', 0)))
      self._finalize_transfer(chat, obj['id'])

    elif t == 'file_cancel':
      self._abort_transfer(chat, obj['id'])

    elif t == 'clear':
      #* собеседник очистил чат — чистим и у себя | peer cleared the chat — clear ours too
      with chat._msg_lock: chat.messages.clear()
      self.emit('chat_cleared', chat=chat)

    elif t == 'destroy':
      #* собеседник убил чат — без ответного destroy
      #* the peer killed the chat — no destroy in reply
      self._destroy_local(chat, reason=obj.get('reason', 'destroy'))

    else:
      self.emit('log', level='WARN', text=f'unknown msg type {t!r}')


  def _on_blob(self, chat, mid, index, total, data):
    #* складываем чанк в буфер передачи            | store the chunk into the transfer
    tr = chat.transfers_in.get(mid)
    if tr is None:
      #? чанк пришёл без меты — игнорируем, ничего не знаем
      #? a chunk without metadata — ignore, we know nothing
      return

    tr['total_chunks'] = total
    tr['received'] += len(data)
    tr['sha'].update(data)
    tr['tmp'].write(data)

    meta = tr['meta']
    if tr['received'] >= int(meta['size']):
      self._finalize_transfer(chat, mid)


  def _finalize_transfer(self, chat, mid):
    #* приём завершён: закрываем файл, проверяем хэш
    #* receive finished: close the file, verify the hash
    tr = chat.transfers_in.pop(mid, None)
    if tr is None: return

    tr['tmp'].flush()
    tr['tmp'].close()

    meta = tr['meta']
    sha = tr['sha'].hexdigest()
    expected = meta.get('sha256', '')
    #! хэш не сошёлся — файл битый, выбрасываем    | hash mismatch — throw away
    if expected and sha != expected:
      try: os.remove(tr['path'])
      except OSError: pass
      self.emit('transfer_error', chat=chat, mid=mid, error='hash mismatch')
      return

    #* переименовываем .part в нормальный файл с оригинальным именем,
    #* чтобы его можно было открыть и сохранить как есть
    #* rename the .part into a proper file with the original name,
    #* so it can be opened and saved as is
    final = self._final_path(chat, meta.get('name', 'file'))
    size = int(meta['size'])

    msg = {'id': mid, 'kind': meta['kind'], 'mine': False, 'name': meta.get('name', ''),
           'size': size, 'path': None, 'sha256': sha, 'ts': time.time()}

    #* файлы до RAM_FILE_MAX_MB держим в памяти и диск не засираем
    #* files up to RAM_FILE_MAX_MB stay in RAM and never touch the disk
    if size <= CONFIG.RAM_FILE_MAX_MB * 1024 * 1024:
      try:
        with open(tr['path'], 'rb') as f:
          data = f.read()
      except OSError:
        data = None
      if data is not None:
        msg['data'] = data
        try: os.remove(tr['path'])
        except OSError: pass
        with chat._msg_lock: chat.messages.append(msg)
        self.emit('transfer_done', chat=chat, msg=msg)
        return

    #* крупный файл — остаётся на диске, но с нормальным именем
    #* a big file stays on disk, but under a proper name
    try:
      os.replace(tr['path'], final)
    except OSError:
      final = tr['path']
    msg['path'] = final

    if meta['kind'] == 'image':
      #* картинку грузим в память для показа        | load the image into memory to display
      try:
        with open(final, 'rb') as f: msg['data'] = f.read()
      except OSError as exc:
        self.emit('transfer_error', chat=chat, mid=mid, error=str(exc))
        return

    with chat._msg_lock: chat.messages.append(msg)
    self.emit('transfer_done', chat=chat, msg=msg)


  def wipe_disk_data(self):
    #* кнопка «Удалить все данные»: стирает принятые файлы, недокачанные
    #* передачи и любые остатки из временной папки
    #* the "delete all data" button: wipes received files, partial
    #* transfers and any leftovers from the temp folder
    try:
      if os.path.isdir(CONFIG.TMP_DIR):
        for entry in os.listdir(CONFIG.TMP_DIR):
          p = os.path.join(CONFIG.TMP_DIR, entry)
          try:
            if os.path.isdir(p):
              shutil.rmtree(p, ignore_errors=True)
            else:
              os.remove(p)
          except OSError:
            pass
      return True
    except OSError:
      return False


  def _final_path(self, chat, name):
    #* безопасное место для принятого файла: tmp/код_чата/имя
    #* a safe home for a received file: tmp/chat_code/name
    base = os.path.basename((name or 'file').replace('\\', '/'))
    if not base:
      base = 'file'
    d = os.path.join(CONFIG.TMP_DIR, 'incoming', chat.code)
    try: os.makedirs(d, exist_ok=True)
    except OSError: return os.path.join(CONFIG.TMP_DIR, base)
    final = os.path.join(d, base)
    if not os.path.exists(final):
      return final
    #? одинаковые имена не перезаписываем: имя (1), имя (2), …
    #? do not overwrite duplicates: name (1), name (2), …
    stem, ext = os.path.splitext(base)
    i = 1
    while os.path.exists(final):
      final = os.path.join(d, f'{stem} ({i}){ext}')
      i += 1
    return final


  def _abort_transfer(self, chat, mid):
    #* отменяем приём, убираем временный файл      | abort receive, drop the temp file
    tr = chat.transfers_in.pop(mid, None)
    if tr is None: return
    try: tr['tmp'].close()
    except OSError: pass
    try: os.remove(tr['path'])
    except OSError: pass


  #/ --- отправка (sending) ---------------------------------------------------------

  def send_text(self, code, text):
    #* отправка текста + своя копия в список       | send text + our copy in the list
    chat = self.chats.get(code)
    if chat is None or chat.state != CHAT_ACTIVE: return False

    mid = crypto.new_msg_id()
    msg = {'id': mid, 'kind': 'text', 'mine': True, 'text': text, 'ts': time.time()}
    with chat._msg_lock: chat.messages.append(msg)
    chat.conn.send_json({'t': 'text', 'id': mid, 'text': text})
    self.emit('message_text', chat=chat, msg=msg)
    return True


  def send_image(self, code, name, data):
    #* отправка картинки из буфера (вставка/файл)  | send an image from a buffer (paste/file)
    chat = self.chats.get(code)
    if chat is None or chat.state != CHAT_ACTIVE: return False

    mid = crypto.new_msg_id()
    msg = {'id': mid, 'kind': 'image', 'mine': True, 'name': name, 'size': len(data), 'data': data,
           'status': 'sending', 'ts': time.time()}
    with chat._msg_lock: chat.messages.append(msg)
    self.emit('message_text', chat=chat, msg=msg)

    #* стримим чанками в отдельном потоке          | stream in chunks on a separate thread
    threading.Thread(target=self._stream_send, args=(chat, mid, name, 'image', data), daemon=True, name='send-img').start()
    return True


  def send_file(self, code, path):
    #* отправка файла с диска                      | send a file from disk
    chat = self.chats.get(code)
    if chat is None or chat.state != CHAT_ACTIVE: return False
    if not os.path.isfile(path): return False

    name = os.path.basename(path)
    size = os.path.getsize(path)
    limit = CONFIG.MAX_FILE_MB * 1024 * 1024
    if limit and size > limit:
      self.emit('transfer_error', chat=chat, mid='', error='too_large')
      return False

    #* картинки, выбранные файлом, показываем в чате сразу как фото
    #* images picked as files are shown in the chat as photos right away
    ext = os.path.splitext(name)[1].lower()
    kind = 'image' if ext in CONFIG.IMAGE_EXTS else 'file'

    mid = crypto.new_msg_id()
    msg = {'id': mid, 'kind': kind, 'mine': True, 'name': name, 'size': size, 'path': path,
           'status': 'sending', 'ts': time.time()}
    with chat._msg_lock: chat.messages.append(msg)
    self.emit('message_text', chat=chat, msg=msg)

    threading.Thread(target=self._stream_send, args=(chat, mid, name, kind, path), daemon=True, name='send-file').start()
    return True


  def _stream_send(self, chat, mid, name, kind, source):
    #* общий конвейер: мета → чанки → done         | shared pipeline: meta → chunks → done
    chunk_bytes = CONFIG.CHUNK_KB * 1024

    if kind == 'image':
      #? картинка может прийти байтами (вставка) или путём (выбранный файл)
      #? an image may come as bytes (paste) or as a path (picked file)
      if isinstance(source, str):
        with open(source, 'rb') as f: source = f.read()
      size = len(source)
      total = max(1, -(-size // chunk_bytes)) if size else 1
      def chunks():
        for i in range(0, size, chunk_bytes):
          yield source[i:i + chunk_bytes]
      chunk_iter = chunks()
    else:
      size = os.path.getsize(source)
      total = max(1, -(-size // chunk_bytes)) if size else 1
      chunk_iter = self._file_chunks(source, chunk_bytes)

    sha = hashlib.sha256()
    meta = {'t': 'file_meta', 'id': mid, 'name': name, 'size': size, 'kind': kind, 'sha256': ''}
    chat.conn.send_json(meta)

    index = 0
    for chunk in chunk_iter:
      sha.update(chunk)
      chat.conn.send_blob(mid, index, total, chunk)
      index += 1

    #* итоговый хэш уходит в file_done            | the final hash goes with file_done
    chat.conn.send_json({'t': 'file_done', 'id': mid, 'sha256': sha.hexdigest(), 'size': size})

    #* помечаем своё сообщение доставленным        | mark our message as delivered
    for m in chat.messages:
      if m.get('id') == mid:
        m['status'] = 'sent'
        break
    self.emit('transfer_done', chat=chat, msg={'id': mid, 'kind': kind, 'name': name, 'size': size, 'mine': True})


  def _file_chunks(self, path, chunk_bytes):
    #* поштучная подача кусков с диска             | feed disk chunks one by one
    with open(path, 'rb') as f:
      while True:
        chunk = f.read(chunk_bytes)
        if not chunk: break
        yield chunk


  #/ --- очистка и уничтожение (clear & destroy) -----------------------------------

  def clear_chat(self, code):
    #* очистить переписку у обоих                  | clear the history on both sides
    chat = self.chats.get(code)
    if chat is None: return
    with chat._msg_lock: chat.messages.clear()
    self.emit('chat_cleared', chat=chat)
    if chat.state == CHAT_ACTIVE:
      chat.conn.send_json({'t': 'clear'})


  def destroy_chat(self, code, reason='destroy'):
    #* публичный вызов: сообщить собеседнику и стереть
    #* public call: tell the peer and wipe
    chat = self.chats.get(code)
    if chat is None: return

    #* best-effort: если связь жива — шлём destroy
    #* best-effort: if the link is alive — send destroy
    if chat.state == CHAT_ACTIVE and chat.conn:
      try: chat.conn.send_json({'t': 'destroy', 'reason': reason})
      except Exception: pass

    self._destroy_local(chat, reason=reason)


  def _destroy_local(self, chat, reason):
    #* внутреннее стирание: закрыть сокет, выкинуть всё
    #* internal wipe: close the socket, drop everything
    if chat.state == CHAT_CLOSED: return
    chat.state = CHAT_CLOSED

    if chat.conn:
      chat.conn.close()

    with self._lock:
      self.chats.pop(chat.code, None)

    #* подчищаем временные файлы недокачанного    | clean up partial temp files
    for tr in list(chat.transfers_in.values()):
      try: tr['tmp'].close()
      except OSError: pass
      try: os.remove(tr['path'])
      except OSError: pass
    chat.transfers_in.clear()

    #* и папку с уже принятыми файлами этого чата  | and the folder of received files
    incoming = os.path.join(CONFIG.TMP_DIR, 'incoming', chat.code)
    try:
      if os.path.isdir(incoming):
        for f in os.listdir(incoming):
          try: os.remove(os.path.join(incoming, f))
          except OSError: pass
        os.rmdir(incoming)
    except OSError:
      pass

    self.emit('chat_closed', chat=chat, reason=reason)


  #/ --- служебное (housekeeping) ---------------------------------------------------

  #* тикаем раз в секунду и следим за таймерами    | tick each second, watch the timers
  def _timer_loop(self):
    while not self._stopping:
      time.sleep(1.0)
      now = time.time()
      #? снимок списка, чтобы не ходить под локом  | a snapshot to avoid locking
      for chat in list(self.chats.values()):
        if chat.expiry_ts and now >= chat.expiry_ts:
          self.emit('log', level='INFO', text='chat timer expired, destroying')
          #* таймер истёк — чат умирает у обоих    | timer expired — the chat dies on both sides
          self.destroy_chat(chat.code, reason='timer')


  def shutdown(self):
    #* полный выход: все чаты, все соединения      | full exit: all chats, all sockets
    self._stopping = True
    self.stop_server()
    for code in list(self.chats.keys()):
      #? при выходе программы шлём destroy, если успеем
      #? on app exit send destroy if we can
      self.destroy_chat(code, reason='app_quit')


  def _safe_close(self, sock):
    try: sock.close()
    except OSError: pass
