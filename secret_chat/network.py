#/ ============================================================================
#/  network.py — TCP-сервер, клиент и живое соединение
#/  network.py — TCP server, client and the live connection
#/ ============================================================================
#/  топология простая: каждый запуск слушает свой порт. Тот, кто
#/  подключается, играет роль клиента, остальные подключаются к нему.
#/  После рукопожатия сокет один и он двусторонний — никаких повторных
#/  соединений не нужно.
#/
#/  simple topology: every instance listens on its own port. The one who
#/  joins acts as a client, everyone else connects to it. After the
#/  handshake a single socket is used in both directions — no reconnect.

import socket
import threading
import time

import config as CONFIG
from . import protocol
from .crypto import aes_encrypt, aes_decrypt


#/ ----------------------------------------------------------------------------
#/  ChatConnection — обёртка над сокетом с шифрованием и keepalive
#/  ChatConnection — socket wrapper with encryption and keepalive
#/ ----------------------------------------------------------------------------
class ChatConnection:

  #* один сокет, общий ключ, колбэки: json / чанк / смерть связи
  #* one socket, one shared key, callbacks: json / chunk / link death
  def __init__(self, sock, aes_key, on_json, on_blob, on_dead):
    self._sock = sock
    self._key = aes_key
    self._on_json = on_json
    self._on_blob = on_blob
    self._on_dead = on_dead

    self._send_lock = threading.Lock()
    self._closed = threading.Event()
    self._last_recv = time.time()

    #? потоки-демоны: если главный процесс умрёт — они не помешают выходу
    #? daemon threads: if the main process dies they won't block the exit
    self._reader = threading.Thread(target=self._read_loop, daemon=True, name='chat-reader')
    self._pinger = threading.Thread(target=self._ping_loop, daemon=True, name='chat-pinger')


  #* запуск чтения и пинга            | start reading and pinging
  def start(self):
    self._sock.settimeout(CONFIG.KEEPALIVE_TIMEOUT)
    self._reader.start()
    self._pinger.start()


  #* зашифрованное JSON-сообщение      | one encrypted JSON message
  def send_json(self, obj):
    #! сеть умерла — не взрываемся, просто молча роняем соединение
    #! network died — don't explode, just silently drop the link
    try:
      with self._send_lock:
        protocol.write_frame(self._sock, protocol.FT_ENC_JSON, aes_encrypt(self._key, protocol.json.dumps(obj, ensure_ascii=False).encode('utf-8')))
    except (OSError, ConnectionError):
      self._mark_dead()


  #* зашифрованный кусок файла         | one encrypted file chunk
  def send_blob(self, msg_id, index, total, chunk):
    try:
      with self._send_lock:
        protocol.write_frame(self._sock, protocol.FT_ENC_BLOB, aes_encrypt(self._key, protocol.BLOB_HEADER.pack(msg_id.encode('ascii'), index, total, len(chunk)) + chunk))
    except (OSError, ConnectionError):
      self._mark_dead()


  #* жива ли ещё связь                | is the link still alive
  def is_alive(self):
    return not self._closed.is_set() and (time.time() - self._last_recv) < CONFIG.KEEPALIVE_TIMEOUT * 2


  #* корректно закрыть                | close cleanly
  def close(self):
    self._closed.set()
    try: self._sock.shutdown(socket.SHUT_RDWR)
    except OSError: pass
    try: self._sock.close()
    except OSError: pass


  #* основной цикл чтения кадров       | main frame-reading loop
  def _read_loop(self):
    #/ читаем, пока сокет жив
    #/ keep reading while the socket is alive
    try:
      while not self._closed.is_set():
        ftype, payload = protocol.read_frame(self._sock)
        self._last_recv = time.time()

        if ftype == protocol.FT_ENC_JSON:
          obj = protocol.json.loads(aes_decrypt(self._key, payload).decode('utf-8'))
          #? колбэк вызываем на потоке чтения — менеджер сам разведёт по потокам
          #? call the callback on the reader thread — the manager routes it
          try: self._on_json(obj)
          except Exception: self._mark_dead()

        elif ftype == protocol.FT_ENC_BLOB:
          plain = aes_decrypt(self._key, payload)
          mid, index, total, size = protocol.BLOB_HEADER.unpack_from(plain, 0)
          data = plain[protocol.BLOB_HEADER_SIZE:]
          try: self._on_blob(mid.decode('ascii'), index, total, data)
          except Exception: self._mark_dead()

    except (OSError, ConnectionError, ValueError):
      #! любая ошибка чтения = конец связи  | any read error = end of link
      self._mark_dead()


  #* раз в N секунд шлём ping, чтобы связь не заснула
  #* every N seconds send a ping so the link never goes idle
  def _ping_loop(self):
    while not self._closed.is_set():
      time.sleep(CONFIG.KEEPALIVE_INTERVAL)
      self.send_json({'t': 'ping'})

    #/ тихо выходим, если соединение уже закрыто
    #/ exit quietly if the connection is already closed
    return


  #* сигнализируем о смерти связи      | announce the link death
  def _mark_dead(self):
    if self._closed.is_set(): return
    self._closed.set()
    try: self._sock.close()
    except OSError: pass
    #! колбэк должен быть идемпотентным — вызывается один раз
    #! the callback must be idempotent — it is called once
    try: self._on_dead()
    except Exception: pass


#/ ----------------------------------------------------------------------------
#/  NetworkServer — слушает порт и принимает входящие
#/  NetworkServer — listens on a port and accepts incoming
#/ ----------------------------------------------------------------------------
class NetworkServer:

  #* менеджер решает, что делать с новым входящим соединением
  #* the manager decides what to do with each new incoming connection
  def __init__(self, manager, port):
    self._manager = manager
    self.port = port
    self._stop = threading.Event()
    self._thread = threading.Thread(target=self._accept_loop, daemon=True, name='p2p-server')


  #* поднять сервер, вернуть реальный порт или None при неудаче
  #* start the server, return the real port or None on failure
  def start(self):
    try:
      self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      #? allow_address_reuse спасает после быстрого перезапуска | helps after quick restarts
      self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      self._sock.bind((CONFIG.BIND_HOST, self.port))
      self._sock.listen(8)
      self._sock.settimeout(1.0)
      self._thread.start()
      return self.port

    except OSError as exc:
      #! не смогли занять порт — вернём ошибку, приложение решит, что делать
      #! couldn't grab the port — return the error, the app decides what to do
      try: self._sock.close()
      except OSError: pass
      return exc


  #* остановить сервер                  | stop the server
  def stop(self):
    self._stop.set()
    try: self._sock.close()
    except OSError: pass


  #* цикл приёма соединений             | connection-accept loop
  def _accept_loop(self):
    while not self._stop.is_set():
      try:
        conn, addr = self._sock.accept()
      except socket.timeout:
        continue
      except OSError:
        break

      #* каждое входящее — в своём потоке, чтобы один тормоз не всё ломал
      #* each incoming gets its own thread so one slow peer can't break all
      threading.Thread(target=self._manager.handle_inbound, args=(conn, addr), daemon=True, name='inbound').start()


#/ ----------------------------------------------------------------------------
#/  connect_to — простой клиентский коннект
#/  connect_to — a plain client connect
#/ ----------------------------------------------------------------------------

def connect_to(ip, port):
  #* свой таймаут, чтобы не висеть вечно на недоступном IP
  #* own timeout so we never hang forever on an unreachable IP
  sock = socket.create_connection((ip, port), timeout=CONFIG.CONNECT_TIMEOUT)

  return sock
