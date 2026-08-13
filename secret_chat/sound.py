#/ ============================================================================
#/  sound.py — мягкий синтезированный «колокольчик» на входящее сообщение
#/  sound.py — a soft synthesized "chime" for an incoming message
#/ ============================================================================
#/  звук генерируется в память и пишется в tmp один раз — никаких внешних
#/  файлов в репозитории. работает через QtMultimedia, если оно доступно.
#/  the chime is synthesized into memory and written to tmp once — no external
#/  files in the repo. works via QtMultimedia when available.

import math
import os
import struct
import tempfile
import threading
import wave

import config as CONFIG


#/ ленивый синглтон — создаётся при первом же проигрывании
#/ lazy singleton — created on the very first playback
_effect = None
_effect_lock = threading.Lock()
_beep_path = None


def _synthesize_chime(path):
  #* два мягких переливающихся тона (как «динь-донь»), огибающая-синус
  #* two softly overlapping tones (a "ding-dong"), sine envelope
  rate = 44100
  total = int(rate * 0.36)
  buf = [0.0] * total

  #? (частота, старт с, длительность, громкость) |  (frequency, start s, duration s, gain)
  notes = [
    (659.25, 0.000, 0.14, 0.60),   # E5
    (987.77, 0.095, 0.24, 0.38),   # B5 — второй тон накладывается мягко
  ]

  for freq, start, dur, gain in notes:
    s0 = int(start * rate)
    n = int(dur * rate)
    for i in range(n):
      idx = s0 + i
      if idx >= total:
        break
      t = i / n
      #* sin(pi*t) даёт и атаку, и спад — ни щелчков, ни резкости
      #* sin(pi*t) gives both attack and release — no clicks, no harshness
      env = math.sin(math.pi * t)
      #* основная частота + обертон для тёплого тембра |  fundamental + an overtone for warmth
      s = math.sin(2 * math.pi * freq * i / rate) + 0.22 * math.sin(2 * math.pi * 2 * freq * i / rate)
      buf[idx] += gain * env * s

  #* нормируем, чтобы не было перегрузки          |  normalize so there is no clipping
  peak = max(1e-9, max(abs(x) for x in buf))
  data = bytearray()
  for x in buf:
    v = int((x / peak) * 0.55 * 32767)
    data += struct.pack('<h', v)

  with wave.open(path, 'wb') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(bytes(data))


def _ensure_effect():
  global _effect, _beep_path
  with _effect_lock:
    if _effect is not None:
      return _effect
    try:
      #? импорт Qt здесь, чтобы головой тест не тянул GUI-зависимости
      #? import Qt here so the headless test never pulls GUI dependencies
      from PySide6.QtMultimedia import QSoundEffect
      from PySide6.QtCore import QUrl

      fd, _beep_path = tempfile.mkstemp(suffix='.wav', prefix='secretchat_', dir=CONFIG.TMP_DIR or None)
      os.close(fd)
      os.makedirs(os.path.dirname(_beep_path), exist_ok=True)
      _synthesize_chime(_beep_path)

      effect = QSoundEffect()
      effect.setSource(QUrl.fromLocalFile(_beep_path))
      effect.setVolume(0.5)
      _effect = effect
    except Exception:
      #! звук не критичен — без него живём          |  sound is not critical — we live without it
      _effect = False
    return _effect


def play_incoming():
  #* если звук выключен — тишина (учитываем и runtime-настройку)
  #* if sound is off — stay quiet (the runtime setting counts too)
  from . import prefs
  if not prefs.effective('sound_on', CONFIG.SOUND_ON):
    return
  effect = _ensure_effect()
  if effect:
    effect.play()
  else:
    try:
      #* самый грубый фолбэк — системный бип       |  the crudest fallback — a system beep
      from PySide6.QtWidgets import QApplication
      QApplication.beep()
    except Exception:
      pass
