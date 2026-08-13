#/ ============================================================================
#/  i18n.py — словари RU/EN и «переводчик»
#/  i18n.py — RU/EN dictionaries and the translator
#/ ============================================================================
#/  все строки интерфейса лежат здесь. добавить язык = добавить словарь.
#/  every UI string lives here. adding a language = adding a dictionary.

import config as CONFIG


#/ текущий язык  |  current language
LANG = CONFIG.LANGUAGE


#/ ----------------------------------------------------------------------------
#/  словари  |  dictionaries
#/ ----------------------------------------------------------------------------
STRINGS = {

'en': {
  'app_title': 'SecretChat',
  'new_chat': 'New chat',
  'join': 'Connect',
  'settings': 'Settings',
  'save': 'Save',
  'my_ip': 'My IP',
  'external_ip': 'Public IP',
  'lan_ip': 'LAN IP',
  'close': 'Close',
  'ok': 'OK',
  'cancel': 'Cancel',
  'copy': 'Copy',
  'copied': 'Copied!',
  'waiting': 'Waiting for a connection…',
  'connected': 'Connected',
  'connecting': 'Connecting…',
  'peer': 'Peer',
  'code': 'Code',
  'port': 'Port',
  'ip': 'IP address',
  'send': 'Send',
  'attach': 'Attach',
  'clear': 'Clear',
  'delete': 'Delete',
  'leave': 'Leave',
  'msg_placeholder': 'Message…',
  'chats': 'Chats',
  'no_chats': 'No chats yet',
  'create_or_join': 'Create a chat or connect to a peer',
  'destroy_in': 'Erases in',
  'unlimited': 'unlimited',
  'error': 'Error',
  'conn_failed': 'Connection failed',
  'code_hint': 'Tell the peer your IP and this code',
  'timer_question': 'Delete this chat after',
  'create_chat': 'Create chat',
  'join_chat': 'Connect to a chat',
  'theme': 'Theme',
  'language': 'Language',
  'sound': 'Sound',
  'on': 'On',
  'off': 'Off',
  'file': 'File',
  'image': 'Image',
  'open': 'Open',
  'save': 'Save',
  'saved': 'Saved',
  'save_failed': 'Could not save the file',
  'delete_all': 'Delete all data',
  'delete_all_confirm': 'Wipe all received files and leftovers from disk?',
  'deleted_all': 'Done',
  'delete_confirm': 'Delete this chat on both sides?',
  'copy_code': 'Copy the code',
  'copy_invite': 'Copy the invite',
  'invite_hint': 'This one line has your IP, port and code — just send it. The peer pastes it and connects at once.',
  'invite_parsed': 'Invite recognized — IP, port and code filled in.',
  'code_or_invite_placeholder': 'XXXX-XXXX-…  (or paste the whole invite line here)',
  'external_ip_note': 'A STUN query is a standard P2P step, no personal data.',
  'nat_hint': 'If the peer is behind NAT without port forwarding, the connection may fail. On a LAN it always works.',
  'listening': 'Listening on port',
  'port_changed': 'Server restarted on port',
  'timers': {
    0: 'never (keep until closed)', 5: '5 min', 30: '30 min', 60: '1 hour',
    120: '2 hours', 360: '6 hours', 1440: '24 hours',
  },
  'theme_names': {
    'black': 'Black', 'white': 'White', 'darkblue': 'Dark blue', 'green': 'Green',
    'purple': 'Purple', 'red': 'Red', 'orange': 'Orange', 'pink': 'Pink',
    'gray': 'Gray', 'teal': 'Teal', 'amber': 'Amber', 'forest': 'Forest',
    'hacker': 'Hacker', 'ultrablack': 'Ultra black',
  },
  'err_bad_code': 'The code is wrong (typo or checksum).',
  'err_timeout': 'Connection timed out.',
  'err_refused': 'Connection refused — is the app running on the peer side?',
  'err_rejected': 'Rejected by the peer:',
  'err_wrong_peer': 'Security check failed — key mismatch.',
  'err_unknown': 'Connection error:',
  'sending': 'sending…',
  'sent': 'sent',
  'too_large': 'File is too large.',
  'pasted_image': 'pasted image',
  'photos': 'Photos',
  'attachments': 'attachments',
  'exit_confirm': 'All chats are erased on close. Close anyway?',
  'connecting_hint': 'Enter the peer IP and the code you got.',
  'auto_destroy': 'auto-delete',
  'press_enter': 'Enter to send, Shift+Enter for a new line',
},

'ru': {
  'app_title': 'SecretChat',
  'new_chat': 'Новый чат',
  'join': 'Подключиться',
  'settings': 'Настройки',
  'save': 'Сохранить',
  'my_ip': 'Мой IP',
  'external_ip': 'Внешний IP',
  'lan_ip': 'Локальный IP',
  'close': 'Закрыть',
  'ok': 'ОК',
  'cancel': 'Отмена',
  'copy': 'Копировать',
  'copied': 'Скопировано!',
  'waiting': 'Ожидание подключения…',
  'connected': 'Подключено',
  'connecting': 'Подключение…',
  'peer': 'Собеседник',
  'code': 'Код',
  'port': 'Порт',
  'ip': 'IP-адрес',
  'send': 'Отправить',
  'attach': 'Файл',
  'clear': 'Очистить',
  'delete': 'Удалить',
  'leave': 'Покинуть',
  'msg_placeholder': 'Сообщение…',
  'chats': 'Чаты',
  'no_chats': 'Чатов пока нет',
  'create_or_join': 'Создай чат или подключись к собеседнику',
  'destroy_in': 'Стирается через',
  'unlimited': 'без таймера',
  'error': 'Ошибка',
  'conn_failed': 'Не удалось подключиться',
  'code_hint': 'Передай собеседнику свой IP и этот код',
  'timer_question': 'Через сколько удалить этот чат?',
  'create_chat': 'Создать чат',
  'join_chat': 'Подключиться к чату',
  'theme': 'Тема',
  'language': 'Язык',
  'sound': 'Звук',
  'on': 'Вкл',
  'off': 'Выкл',
  'file': 'Файл',
  'image': 'Изображение',
  'open': 'Открыть',
  'save': 'Сохранить',
  'saved': 'Сохранено',
  'save_failed': 'Не удалось сохранить файл',
  'delete_all': 'Удалить все данные',
  'delete_all_confirm': 'Стереть с диска все принятые файлы и остатки?',
  'deleted_all': 'Готово',
  'delete_confirm': 'Удалить этот чат у обоих?',
  'copy_code': 'Скопировать код',
  'copy_invite': 'Скопировать приглашение',
  'invite_hint': 'В этой строке сразу твой IP, порт и код — просто отправь её. Собеседник вставит и сразу подключится.',
  'invite_parsed': 'Приглашение распознано — IP, порт и код заполнены.',
  'code_or_invite_placeholder': 'XXXX-XXXX-…  (или вставь сюда всё приглашение)',
  'external_ip_note': 'Запрос к STUN-серверу — стандартный шаг P2P, личные данные не отправляются.',
  'nat_hint': 'Если собеседник за роутером без проброса порта, подключение может не пройти. В локальной сети работает всегда.',
  'listening': 'Слушаю порт',
  'port_changed': 'Сервер перезапущен на порту',
  'timers': {
    0: 'не ограничено (пока не закроешь)', 5: '5 минут', 30: '30 минут', 60: '1 час',
    120: '2 часа', 360: '6 часов', 1440: '24 часа',
  },
  'theme_names': {
    'black': 'Чёрная', 'white': 'Белая', 'darkblue': 'Тёмно-синяя', 'green': 'Зелёная',
    'purple': 'Фиолетовая', 'red': 'Красная', 'orange': 'Оранжевая', 'pink': 'Розовая',
    'gray': 'Серая', 'teal': 'Бирюзовая', 'amber': 'Янтарная', 'forest': 'Лесная',
    'hacker': 'Хакер', 'ultrablack': 'Ультра-чёрная',
  },
  'err_bad_code': 'Код неверный (опечатка или контрольная сумма).',
  'err_timeout': 'Истекло время подключения.',
  'err_refused': 'Соединение отклонено — запущено ли приложение у собеседника?',
  'err_rejected': 'Собеседник отклонил:',
  'err_wrong_peer': 'Не прошла проверка безопасности — ключи не совпали.',
  'err_unknown': 'Ошибка подключения:',
  'sending': 'отправка…',
  'sent': 'отправлено',
  'too_large': 'Файл слишком большой.',
  'pasted_image': 'вставленное фото',
  'photos': 'Фото',
  'attachments': 'вложений',
  'exit_confirm': 'Все чаты сотрутся при закрытии. Закрыть?',
  'connecting_hint': 'Введи IP собеседника и код, который он тебе дал.',
  'auto_destroy': 'автоудаление',
  'press_enter': 'Enter — отправить, Shift+Enter — новая строка',
},

}


def set_lang(lang):
  #* меняем язык на лету                        |  switch the language on the fly
  global LANG
  LANG = lang


def tr(key, **kw):
  #* ищем в текущем языке, падаем на английский  |  look in the current language, fall back to EN
  table = STRINGS.get(LANG) or STRINGS['en']
  s = table.get(key)
  if s is None:
    s = STRINGS['en'].get(key, key)
  #* подстановка {x}                             |  {x} substitution
  for k, v in kw.items():
    s = s.replace('{' + k + '}', str(v))
  return s


def theme_name(theme_id):
  #* локализованное имя темы                    |  the localized theme name
  return tr('theme_names').get(theme_id, theme_id)


def timer_label(minutes):
  #* человекочитаемая подпись таймера           |  human-readable timer label
  return tr('timers').get(int(minutes), f'{minutes} min')
