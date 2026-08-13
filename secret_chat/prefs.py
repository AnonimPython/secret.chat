#/ ============================================================================
#/  prefs.py — runtime-настройки (тема/язык/порт), которые перекрывают config.py
#/  prefs.py — runtime settings (theme/language/port) overriding config.py
#/ ============================================================================
#/  config.py — это «заводские» значения. То, что юзер меняет в диалоге
#/  «Настройки», сохраняется здесь и перекрывает заводские до тех пор,
#/  пока ALLOW_RUNTIME_OVERRIDES = True в конфиге.
#/
#/  config.py holds the "factory" values. Whatever the user changes in the
#/  Settings dialog is saved here and overrides the factory ones until
#/  ALLOW_RUNTIME_OVERRIDES = True in the config.

import json
import os

import config as CONFIG


#/ где лежат runtime-настройки  |  where the runtime settings live
_PREFS_DIR = os.path.join(os.path.expanduser('~'), '.secret_chat')
_PREFS_PATH = os.path.join(_PREFS_DIR, 'prefs.json')


#/ кэш загруженных значений  |  cache of loaded values
_cache = None


def _load():
  #* тянем файл один раз за процесс               |  read the file once per process
  global _cache
  if _cache is not None:
    return _cache
  try:
    with open(_PREFS_PATH, 'r', encoding='utf-8') as f:
      _cache = json.load(f)
  except (OSError, ValueError):
    #! файла нет или он битый — начинаем с пустого |  missing or broken — start empty
    _cache = {}
  return _cache


def get(key):
  #* runtime-значение, если есть и разрешено       |  runtime value if present and allowed
  if not CONFIG.ALLOW_RUNTIME_OVERRIDES:
    return None
  return _load().get(key)


def effective(key, default):
  #* значение с учётом перекрытий                  |  the value honouring overrides
  return get(key) if get(key) is not None else default


def set(key, value):
  #* сохраняем перекрытие и обновляем кэш          |  save an override and refresh the cache
  data = _load()
  data[key] = value
  os.makedirs(_PREFS_DIR, exist_ok=True)
  with open(_PREFS_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
  _cache = data
