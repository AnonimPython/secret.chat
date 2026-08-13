#/ ============================================================================
#/  test_e2e.py — сквозной тест ядра без GUI
#/  test_e2e.py — end-to-end core test without any GUI
#/ ============================================================================
#/  запуск:  python -m pytest tests/test_e2e.py -v      (или python tests/test_e2e.py)
#/  run:      python -m pytest tests/test_e2e.py -v      (or python tests/test_e2e.py)

import io
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from secret_chat import crypto
from secret_chat import manager as m


#/ копилка событий: каждое событие отдаётся ровно один раз  |  each event is delivered exactly once
class Pouch:

  def __init__(self):
    self.events = {}
    self._seen = {}
    self._cond = threading.Condition()

  def on(self, event):
    def _reg(**kw):
      with self._cond:
        self.events.setdefault(event, []).append(kw)
        self._cond.notify_all()
    return _reg

  def wait_until(self, event, pred=None, timeout=10):
    #* ждём следующее событие, подходящее предикату |  wait for the next event matching the predicate
    end = time.time() + timeout
    with self._cond:
      while True:
        idx = self._seen.get(event, 0)
        for ev in self.events.get(event, [])[idx:]:
          self._seen[event] = self._seen.get(event, 0) + 1
          if pred is None or pred(ev):
            return ev
        if time.time() > end:
          raise TimeoutError(f'no matching event {event}')
        self._cond.wait(timeout=0.2)


def wait_active(mgr, code, timeout=10):
  #* ждём пока чат станет active  |  wait until the chat becomes active
  end = time.time() + timeout
  while time.time() < end:
    chat = mgr.chats.get(code)
    if chat and chat.state == m.CHAT_ACTIVE:
      return chat
    time.sleep(0.05)
  raise TimeoutError('chat never became active')


def test_pairing_code_roundtrip():
  priv, pub = crypto.generate_keypair()
  code = crypto.generate_pairing_code(pub)
  assert '-' in code
  got = crypto.parse_pairing_code(code)
  assert got == pub, 'public key must survive a code roundtrip'


def test_encrypt_decrypt():
  priv1, pub1 = crypto.generate_keypair()
  priv2, pub2 = crypto.generate_keypair()
  s1 = crypto.compute_shared_secret(priv1, pub2)
  s2 = crypto.compute_shared_secret(priv2, pub1)
  k1 = crypto.derive_aes_key(s1, 'CODE')
  k2 = crypto.derive_aes_key(s2, 'CODE')
  blob = crypto.aes_encrypt(k1, b'secret message')
  assert crypto.aes_decrypt(k2, blob) == b'secret message'


def test_full_chat_flow():
  #* два экземпляра приложения на разных портах  |  two app instances on different ports
  A = m.ChatManager(port=43101)
  B = m.ChatManager(port=43102)

  pa, pb = Pouch(), Pouch()
  for ev in ('chat_established', 'chat_closed', 'message_text', 'transfer_done', 'chat_cleared'):
    A.add_handler(ev, pa.on(ev))
    B.add_handler(ev, pb.on(ev))

  #* А создаёт чат, Б подключается по коду       |  A creates a chat, B joins with the code
  code = A.create_chat(0)
  B.join_chat('127.0.0.1', 43101, code)

  chat_a = wait_active(A, code)
  chat_b = wait_active(B, code)
  assert pa.wait_until('chat_established')['chat'] is chat_a
  assert pb.wait_until('chat_established')['chat'] is chat_b

  #* оба направления текста                      |  text both ways
  B.send_text(code, 'privet ot B')
  msg = pa.wait_until('message_text', pred=lambda ev: not ev['msg']['mine'])['msg']
  assert msg['text'] == 'privet ot B' and msg['mine'] is False

  A.send_text(code, 'privet ot A')
  #* B получил чужое сообщение (mine=False)       |  B got the other side's message (mine=False)
  msg = pb.wait_until('message_text', pred=lambda ev: not ev['msg']['mine'])['msg']
  assert msg['text'] == 'privet ot A' and msg['mine'] is False
  #* у A это сообщение появилось как своё (mine=True)
  #* on A's side it showed up as its own (mine=True)
  own = pa.wait_until('message_text', pred=lambda ev: ev['msg']['mine'])['msg']
  assert own['text'] == 'privet ot A' and own['mine'] is True

  #* картинка из буфера                          |  an image from a buffer
  png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 2048
  A.send_image(code, 'photo.png', png)
  got = pb.wait_until('transfer_done', pred=lambda ev: ev['msg']['kind'] == 'image')['msg']
  assert got['kind'] == 'image'
  assert bytes(got['data']) == png

  #* файл с диска                                |  a real file from disk
  with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
    f.write(b'hello file world')
    path = f.name
  B.send_file(code, path)
  got = pa.wait_until('transfer_done', pred=lambda ev: ev['msg']['kind'] == 'file')['msg']
  assert got['kind'] == 'file'
  #* небольшой файл живёт в памяти, диск не трогаем |  a small file lives in RAM, no disk writes
  assert bytes(got['data']) == b'hello file world'
  assert got.get('path') is None

  #* картинка, выбранная файлом, = фото в чате   |  an image picked as a file = a photo in chat
  with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
    f.write(b'\x89PNG\r\n\x1a\n' + os.urandom(2048))
    img_path = f.name
  A.send_file(code, img_path)
  got_img = pb.wait_until('transfer_done', pred=lambda ev: ev['msg']['kind'] == 'image')['msg']
  assert got_img['kind'] == 'image'
  assert 'data' in got_img
  assert got_img.get('path') is None

  #* очистка у обоих                             |  clear on both sides
  A.clear_chat(code)
  pb.wait_until('chat_cleared')
  assert len(chat_b.messages) == 0

  #* уничтожение чата у обоих                    |  destroy on both sides
  B.destroy_chat(code, reason='test')
  assert pa.wait_until('chat_closed')['reason'] == 'test'
  assert code not in A.chats and code not in B.chats

  A.shutdown()
  B.shutdown()


def test_disconnect_erases_chat():
  #* закрытие программы = чат стирается у обоих  |  closing the app = chat wiped on both sides
  A = m.ChatManager(port=43103)
  B = m.ChatManager(port=43104)

  pa, pb = Pouch(), Pouch()
  A.add_handler('chat_closed', pa.on('chat_closed'))
  B.add_handler('chat_closed', pb.on('chat_closed'))

  code = A.create_chat(0)
  B.join_chat('127.0.0.1', 43103, code)
  wait_active(A, code)
  wait_active(B, code)

  #* B «закрывает программу» — сокет падает, A это видит и стирает чат
  #* B "closes the app" — the socket drops, A sees it and wipes the chat
  chat_b = B.chats[code]
  chat_b.conn.close()

  assert pa.wait_until('chat_closed')['reason'] == 'disconnect'
  assert code not in A.chats

  A.shutdown()
  B.shutdown()


def test_wipe_disk_data():
  #* большой файл (лимит в память выключен) идёт на диск; кнопка «Удалить все данные» стирает его
  #* a big file (RAM limit off) goes to disk; the "delete all data" button wipes it
  old_limit = m.CONFIG.RAM_FILE_MAX_MB
  m.CONFIG.RAM_FILE_MAX_MB = 0

  A = m.ChatManager(port=43105)
  B = m.ChatManager(port=43106)
  pb = Pouch()
  B.add_handler('transfer_done', pb.on('transfer_done'))

  try:
    code = A.create_chat(0)
    B.join_chat('127.0.0.1', 43105, code)
    wait_active(A, code)
    wait_active(B, code)

    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
      f.write(b'z' * 4096)
      p = f.name
    A.send_file(code, p)
    got = pb.wait_until('transfer_done', pred=lambda ev: ev['msg']['kind'] == 'file')['msg']
    assert got['path'] and os.path.isfile(got['path'])

    B.wipe_disk_data()
    assert not os.path.exists(got['path'])
  finally:
    m.CONFIG.RAM_FILE_MAX_MB = old_limit
    A.shutdown()
    B.shutdown()


if __name__ == '__main__':
  test_pairing_code_roundtrip()
  test_encrypt_decrypt()
  test_full_chat_flow()
  test_disconnect_erases_chat()
  test_wipe_disk_data()
  print('ALL CORE TESTS PASSED')
