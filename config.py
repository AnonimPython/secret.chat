#/ ============================================================================
#/  config.py — ГЛАВНЫЙ КОНФИГ ПРОЕКТА. Правится руками, без пересборки.
#/  config.py — THE MASTER CONFIG FILE. Edit by hand, no rebuild needed.
#/ ============================================================================
#/  всё, что написано ниже — обычный Python: меняешь значение — меняется приложение.
#/  everything below is plain Python: change a value and the app changes.
#/  секции (sections): [APP] [NETWORK] [SECURITY] [UI] [LOG] [DOCKER]
#/
#/  подсказка по комментариям (comment legend):
#/    #!   критично / критично
#/    #*   что делает строка / what the line does
#/    #/   структура, разделы / structure, sections
#/    #?   нюансы и причины / nuances and reasons

import os
import tempfile


#/ ----------------------------------------------------------------------------
#/  [APP]  — само приложение
#/  [APP]  — the application itself
#/ ----------------------------------------------------------------------------

#* имя приложения, видно в заголовке окна        | app name, shown in the window title
APP_NAME = "SecretChat"
#* версия, уходит в рукопожатие                  | version, goes into the handshake
APP_VERSION = "1.0.0"
#* язык по умолчанию: ru | en                    | default language: ru | en
LANGUAGE = "ru"
#* тема по умолчанию: см. секцию [UI] ниже       | default theme: see [UI] section below
THEME = "darkblue"
#* звук уведомлений вкл/выкл                     | notification sound on/off
SOUND_ON = True
#* автоматически поднимать свой P2P-сервер       | auto-start your own P2P server
START_SERVER = True

#? если TRUE — поверх настроек из этого файла будут действовать
#? изменения, сделанные в диалоге «Настройки» (хранятся в prefs.json).
#? если FALSE — настройки из диалога работают только до перезапуска.
#? if TRUE, runtime changes made in the Settings dialog (saved in prefs.json)
#? override the values below. if FALSE — dialog changes last until restart.
ALLOW_RUNTIME_OVERRIDES = True


#/ ----------------------------------------------------------------------------
#/  [NETWORK]  — сеть, P2P, keepalive
#/  [NETWORK]  — network, P2P, keepalive
#/ ----------------------------------------------------------------------------

#* порт, на котором слушаем входящие подключения  | port we listen on for incoming
PORT = 42000
#* на каком адресе слушать (не трогай)           | address to bind (leave alone)
BIND_HOST = "0.0.0.0"
#* как часто слать ping собеседнику (сек)        | how often to ping the peer (sec)
KEEPALIVE_INTERVAL = 20
#* если тишина дольше — считаем связь мёртвой    | if silence lasts longer — dead link
KEEPALIVE_TIMEOUT = 120
#* таймаут установки соединения (сек)            | connection-establish timeout (sec)
CONNECT_TIMEOUT = 8
#* при попытке подключения к занятому порту — смещение для следующей попытки
#* when the port is busy, the offset for the next bind attempt
PORT_RETRY_OFFSET = 50

#! P2P через интернет: если ты и собеседник за роутерами без проброса порта
#! и без UPnP — подключение не пройдёт. В локальной сети работает всегда.
#! P2P over the internet: if both sides are behind routers without port
#! forwarding or UPnP — it won't connect. On a LAN it always works.


#/ ----------------------------------------------------------------------------
#/  [SECURITY]  — безопасность и лимиты
#/  [SECURITY]  — security and limits
#/ ----------------------------------------------------------------------------

#* максимальный размер файла в МБ (0 = без лимита) | max file size in MB (0 = unlimited)
MAX_FILE_MB = 512
#* размер чанка при передаче файла, КБ           | file transfer chunk size, KB
CHUNK_KB = 256
#* сколько минут живёт чат по умолчанию, если создатель не выбрал иное
#* default chat lifetime in minutes if the creator does not choose otherwise
DEFAULT_DESTROY_MIN = 0
#* пресеты таймера самоуничтожения (минуты)      | self-destruct timer presets (minutes)
DESTROY_PRESETS = [0, 5, 30, 60, 120, 360, 1440]
#* проверять ли подпись/контрольную сумму кода   | verify the code checksum or not
VERIFY_CODE_CHECKSUM = True

#! сообщения и файлы никогда не пишутся на диск: чат живёт в памяти и стирается
#! при выходе из него. На диске остаётся только tmp-файл недокачанной передачи.
#! messages and files are never written to disk: a chat lives in RAM and is wiped
#! when you leave. Only a partial-transfer tmp file may remain on disk.


#/ ----------------------------------------------------------------------------
#/  [UI]  — вид, шрифты, поведение интерфейса
#/  [UI]  — look, fonts, interface behaviour
#/ ----------------------------------------------------------------------------

#* базовый размер шрифта интерфейса              | base UI font size
FONT_SIZE = 13
#* максимальная ширина пузыря сообщения, px      | max message bubble width, px
BUBBLE_MAX_WIDTH = 360
#* максимальная ширина картинки в чате, px       | max image width in chat, px
IMAGE_MAX_WIDTH = 280
#* сколько вложений можно прицепить за раз       | how many attachments at once
MAX_ATTACHMENTS = 10
#* расширения, которые показываются в чате фото  | extensions shown in the chat as photos
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.heic', '.tif', '.tiff'}
#* принятые файлы до этого размера (МБ) живут в памяти, диск не засирают;
#* крупнее — кладутся во временную папку и удаляются вместе с чатом.
#* received files up to this size (MB) live in RAM and never touch the disk;
#* bigger ones go to a temp folder and are wiped together with the chat.
RAM_FILE_MAX_MB = 25
#* минимальная высота окна                       | minimum window height
WIN_MIN_W = 820
WIN_MIN_H = 520
#* стартовый размер окна                         | starting window size
WIN_W = 900
WIN_H = 560

#/  доступные темы (id → название). чтобы поменять цвета — открой themes.py
#/  available themes (id → name). to change the colors — open themes.py
THEMES = [
    "black", "white", "darkblue", "green", "purple", "red",
    "orange", "pink", "gray", "teal", "amber", "forest",
    "hacker", "ultrablack",
]


#/ ----------------------------------------------------------------------------
#/  [LOG]  — журнал событий (не собирает данные, только для отладки)
#/  [LOG]  — event log (collects nothing, only for debugging)
#/ ----------------------------------------------------------------------------

LOG_ENABLED = True
LOG_LEVEL = "INFO"
#* пустая строка = писать в stderr, иначе путь файла
#* empty string = write to stderr, otherwise a file path
LOG_FILE = ""


#/ ----------------------------------------------------------------------------
#/  [DOCKER]  — окружение для контейнера (GUI запускается на Xvfb)
#/  [DOCKER]  — environment for the container (GUI runs on Xvfb)
#/ ----------------------------------------------------------------------------

#* виртуальный дисплей: ширина x высота x глубина | virtual display: W x H x depth
XVFB_RESOLUTION = "1280x800x24"
#* пароль VNC для доступа к GUI (пусто = без пароля)
#* VNC password to reach the GUI (empty = no password)
VNC_PASSWORD = "secret"
#* порт VNC внутри контейнера                     | VNC port inside the container
VNC_PORT = 5900
#* порт noVNC (браузер) внутри контейнера         | noVNC (browser) port inside container
NOVNC_PORT = 6080


#/ ----------------------------------------------------------------------------
#/  вспомогательное — редко трогается             | helpers — rarely touched
#/ ----------------------------------------------------------------------------

#* куда класть tmp-файлы недокачанных передач     | where partial transfers go
TMP_DIR = os.path.join(tempfile.gettempdir(), "secret_chat_tmp")
#* куда предлагать сохранять файлы (папка Загрузки) | suggested save folder (Downloads)
SAVE_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
#* таймаут чтения кадра рукопожатия, сек          | handshake frame read timeout, sec
HANDSHAKE_READ_TIMEOUT = 15
