#/ ============================================================================
#/  docker/entrypoint.py — поднимает виртуальный дисплей и запускает GUI
#/  docker/entrypoint.py — starts a virtual display and runs the GUI
#/ ============================================================================
#/  цепочка:  Xvfb → x11vnc (VNC) → websockify (noVNC) → само приложение
#/  chain:    Xvfb → x11vnc (VNC) → websockify (noVNC) → the app itself
#/
#/  GUI всегда стартует сам, когда контейнер запускается — это и есть
#/  «программа открывается автоматически».
#/  the GUI always starts on its own when the container runs — that is the
#/  "the program opens automatically" part.

import os
import shutil
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config as CONFIG


#/ где noVNC лежит в Debian-пакете  |  where the noVNC webroot lives on Debian
NOVNC_WEB = '/usr/share/novnc'


def _spawn(cmd):
  #* запускаем процесс, не засоряя stdout        |  spawn a process, keep stdout clean
  proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=None)
  print(f'[*] started: {" ".join(cmd)}', flush=True)
  return proc


def _x11vnc_args():
  #* пароль из конфига; пустой = без пароля (только локальный доступ)
  #* password from config; empty = no password (local access only)
  pw = CONFIG.VNC_PASSWORD
  args = ['x11vnc', '-display', os.environ.get('DISPLAY', ':99'),
          '-rfbport', str(CONFIG.VNC_PORT), '-forever', '-shared', '-noxdamage', '-nopw']
  if pw:
    args = ['x11vnc', '-display', os.environ.get('DISPLAY', ':99'),
            '-rfbport', str(CONFIG.VNC_PORT), '-forever', '-shared', '-noxdamage',
            '-passwd', pw]
  return args


def _noVNC_cmd():
  #* websockify есть и как бинарь, и как модуль  |  websockify is both a binary and a module
  if shutil.which('websockify'):
    return ['websockify', '--web', NOVNC_WEB, str(CONFIG.NOVNC_PORT), f'127.0.0.1:{CONFIG.VNC_PORT}']
  return [sys.executable, '-m', 'websockify', '--web', NOVNC_WEB, str(CONFIG.NOVNC_PORT), f'127.0.0.1:{CONFIG.VNC_PORT}']


def main():
  #! без DISPLAY в контейнере не живём — Xvfb обязателен
  #! without DISPLAY in a container we can't live — Xvfb is a must
  display = os.environ.get('DISPLAY', ':99')
  os.environ['DISPLAY'] = display

  #/ 1. виртуальный дисплей                     |  1. the virtual display
  xvfb = _spawn(['Xvfb', display, '-screen', '0', CONFIG.XVFB_RESOLUTION, '-nolisten', 'tcp'])
  #* даём X-серверу проснуться                   |  give the X server a moment to wake
  time.sleep(1.5)

  #/ 2. VNC-сервер                               |  2. the VNC server
  vnc = _spawn(_x11vnc_args())

  #/ 3. noVNC → браузер                          |  3. noVNC → the browser
  novnc = None
  if shutil.which('websockify') or _has_module():
    novnc = _spawn(_noVNC_cmd())
  else:
    print('[!] websockify not found — GUI only via raw VNC', flush=True)

  #/ 4. само приложение                          |  4. the app itself
  app = _spawn([sys.executable, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'main.py')])

  print('[✓] SecretChat GUI is up', flush=True)
  print(f'    noVNC  (browser):  http://localhost:{CONFIG.NOVNC_PORT}/vnc.html', flush=True)
  print(f'    VNC    (client):   localhost:{CONFIG.VNC_PORT}', flush=True)
  print(f'    P2P    port:       {CONFIG.PORT}', flush=True)

  #/ ждём завершения приложения или сигнал       |  wait for the app or a signal
  def _stop(_s, _f):
    for p in (app, vnc, novnc, xvfb):
      if p: p.terminate()
    sys.exit(0)

  signal.signal(signal.SIGTERM, _stop)
  signal.signal(signal.SIGINT, _stop)

  while True:
    #! приложение упало — гасим всё, контейнер перезапустит
    #! the app crashed — kill everything, the container restarts
    if app.poll() is not None:
      print('[!] app exited, shutting down the display stack', flush=True)
      for p in (vnc, novnc, xvfb):
        if p: p.terminate()
      sys.exit(app.returncode or 1)
    time.sleep(2)


def _has_module():
  #* проверка, что websockify импортируется      |  check that websockify imports
  try:
    import websockify  # noqa: F401
    return True
  except ImportError:
    return False


if __name__ == '__main__':
  main()
