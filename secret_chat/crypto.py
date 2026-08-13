#/ ============================================================================
#/  crypto.py — весь шифр этого приложения живёт только здесь
#/  crypto.py — all the cryptography in this app lives only here
#/ ============================================================================
#/  схема (scheme):
#/    • X25519  — ECDH, общий секрет для пары
#/    • HKDF    — из общего секрета делаем ключ AES-256
#/    • AES-256-GCM — шифрование каждого сообщения, nonce на каждый кадр
#/
#/  pairing code (код подключения) — это, по сути, "сейфти-номер":
#/  внутрь зашит публичный ключ создателя чата. Показал код = показал ключ.
#/  the pairing code is basically a "safety number": the creator's public
#/  key is baked right into it. Showing the code = showing the key.


import base64, hashlib, secrets
import hmac as _hmac

from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


#/ константы кода подключения (pairing code constants)
_CODE_VERSION      = b'\x01'
_CODE_CHECKSUM_LEN = 2
_CODE_GROUP_LEN    = 4

#/ размеры для AES-GCM
_AES_KEY_BYTES   = 32
_GCM_NONCE_BYTES = 12


#/ ----------------------------------------------------------------------------
#/   ключи X25519  |  X25519 key management
#/ ----------------------------------------------------------------------------

def generate_keypair():
    #* fresh private key                  |  свежий приватный ключ
    private = x25519.X25519PrivateKey.generate()
    #* public part as raw 32 bytes        |  публичная часть — сырые 32 байта
    public = private.public_key().public_bytes_raw()

    return private, public


def load_public(public_bytes):
    #? X25519 сам себя не проверяет — проверим длину сами
    #? X25519 does not validate on its own — we check the length ourselves
    if len(public_bytes) != 32:
        raise ValueError('public key must be 32 bytes')
    #* build object from raw bytes        |  собираем объект из сырых байт
    return x25519.X25519PublicKey.from_public_bytes(public_bytes)


def compute_shared_secret(private, peer_public_bytes):
    #* ECDH exchange -> 32 shared bytes  |  ECDH-обмен -> 32 общих байта
    shared = private.exchange(load_public(peer_public_bytes))

    return shared


def derive_aes_key(shared_secret, code):
    #* salt = hash от кода — разные чаты, разные соли
    #* salt = hash of the code — different chats, different salts
    salt = hashlib.sha256(code.encode('utf-8')).digest()[:16]

    #* HKDF-SHA256: один общий секрет -> ключ AES
    #* HKDF-SHA256: one shared secret -> one AES key
    kdf = HKDF(algorithm=hashes.SHA256(), length=_AES_KEY_BYTES, salt=salt, info=b'secret.chat')
    aes_key = kdf.derive(shared_secret)

    return aes_key


#/ ----------------------------------------------------------------------------
#/   AES-256-GCM  |  per-message encryption
#/ ----------------------------------------------------------------------------

def aes_encrypt(aes_key, plaintext):
    #* unique nonce on every call        |  свой nonce на каждый вызов
    nonce = secrets.token_bytes(_GCM_NONCE_BYTES)
    #* returns nonce || ciphertext(+tag)  |  возвращаем nonce + шифротекст(+тег)
    blob = nonce + AESGCM(aes_key).encrypt(nonce, plaintext, None)

    return blob


def aes_decrypt(aes_key, blob):
    #! wrong nonce length = corrupted frame, raise loudly
    #! неверная длина nonce = битый кадр, кидаем ошибку
    if len(blob) < _GCM_NONCE_BYTES + 16:
        raise ValueError('short ciphertext')

    nonce, ct = blob[:_GCM_NONCE_BYTES], blob[_GCM_NONCE_BYTES:]
    #* GCM сам проверяет целостность, иначе — исключение
    #* GCM verifies integrity itself, otherwise it raises
    plaintext = AESGCM(aes_key).decrypt(nonce, ct, None)

    return plaintext


#/ ----------------------------------------------------------------------------
#/   pairing code  |  генерация и разбор
#/ ----------------------------------------------------------------------------

def _code_checksum(body):
    #* короткий checksum от тела — ловит опечатки при вводе
    #* short checksum of the body — catches typos while typing
    return hashlib.sha256(body).digest()[:_CODE_CHECKSUM_LEN]


def generate_pairing_code(public_key_bytes):
    #/  формат: версия(1) + pubkey(32) + checksum(2)  →  base32, группы по 4
    #/  format: version(1) + pubkey(32) + checksum(2)  →  base32, groups of 4

    #* собираем тело                                  |  assemble the body
    body = _CODE_VERSION + public_key_bytes
    #* весь payload                                  |  the full payload
    payload = body + _code_checksum(body)

    #* base32 без '='-хвоста                          |  base32 without padding
    encoded = base64.b32encode(payload).decode('ascii').rstrip('=')
    #* разбиваем на группы и соединяем дефисами       |  group with dashes
    grouped = '-'.join(encoded[i:i + _CODE_GROUP_LEN] for i in range(0, len(encoded), _CODE_GROUP_LEN))

    return grouped


def parse_pairing_code(code):
    #? пользователь мог ввести маленькими буквами и с пробелами
    #? the user may have typed lowercase letters and spaces
    clean = code.replace('-', '').replace(' ', '').upper()
    #* возвращаем base32 к кратной 8 длине           |  pad back to multiple of 8
    clean += '=' * (-len(clean) % 8)

    try:
        payload = base64.b32decode(clean)
    except Exception as exc:
        raise ValueError('bad base32') from exc

    #! версия не та — точно не наш код
    #! wrong version — definitely not our code
    if len(payload) != 1 + 32 + _CODE_CHECKSUM_LEN or payload[:1] != _CODE_VERSION:
        raise ValueError('bad code version')

    body, check = payload[:-_CODE_CHECKSUM_LEN], payload[-_CODE_CHECKSUM_LEN:]
    #! checksum не сошёлся — опечатка при вводе
    #! checksum mismatch — a typo while entering
    if not _hmac.compare_digest(check, _code_checksum(body)):
        raise ValueError('bad checksum')

    return body[1:]


#/ ----------------------------------------------------------------------------
#/   мелочи  |  small helpers
#/ ----------------------------------------------------------------------------

def short_code(code):
    #* для показа в заголовке — только первые две группы
    #* for the header display — only the first two groups
    return '-'.join(code.split('-')[:2]) + '-…'


def new_msg_id():
    #* 8 hex символов на сообщение — хватает с запасом
    #* 8 hex chars per message — more than enough
    return secrets.token_hex(4).upper()
