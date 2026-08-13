#/ ============================================================================
#/  protocol.py — фреймы поверх TCP
#/  protocol.py — frames on top of plain TCP
#/ ============================================================================
#/  каждый кадр: [1 байт тип][4 байта длина (BE)][payload]
#/  each frame:  [1 byte type][4 bytes length (BE)][payload]
#/
#/  типы кадров (frame types):
#/    0x01  ENC_JSON  зашифрованный JSON   | encrypted JSON
#/    0x02  ENC_BLOB  зашифрованный кусок файла | encrypted file chunk
#/    0x10  HS_INIT   рукопожатие (клиент → сервер, открыто) | handshake, plain
#/    0x11  HS_RESP   ответ сервера (открыто)                 | server reply, plain
#/    0x12  HS_ERR    ошибка рукопожатия (открыто)            | handshake error, plain
#/
#/  после рукопожатия ВСЁ шифруется AES-GCM: nonce(12) + ciphertext
#/  after the handshake EVERYTHING is AES-GCM: nonce(12) + ciphertext

import json
import struct

from .crypto import aes_encrypt, aes_decrypt

#? эти константы не менять — они часть протокола
#? do not change these — they are part of the protocol
FT_ENC_JSON = 0x01
FT_ENC_BLOB = 0x02
FT_HS_INIT  = 0x10
FT_HS_RESP  = 0x11
FT_HS_ERR   = 0x12

#* заголовок чанка файла: id(8) + index(4) + total(4) + chunk_size(4)
#* file chunk header: id(8) + index(4) + total(4) + chunk_size(4)
BLOB_HEADER = struct.Struct('>8sIII')
BLOB_HEADER_SIZE = BLOB_HEADER.size


#/ ----------------------------------------------------------------------------
#/  чтение/запись кадров  |  frame read / write
#/ ----------------------------------------------------------------------------

def pack_frame(ftype, payload):
    #* 1 байт тип + 4 байта длина + сам payload      | 1 byte type + 4 byte length + payload
    header = bytes([ftype]) + struct.pack('>I', len(payload))

    return header + payload


def recv_exact(sock, n):
    #* читаем ровно n байт, иначе падаем            | read exactly n bytes or fail
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        #! пустой recv = собеседник закрыл соединение | empty recv = peer closed
        if not chunk:
            raise ConnectionError('peer closed the connection')
        buf += chunk

    return buf


def read_frame(sock):
    #* 5 байт заголовка                              | 5 bytes of header
    head = recv_exact(sock, 5)
    ftype = head[0]
    length = struct.unpack('>I', head[1:5])[0]
    #! не даём съесть всю память гигантским кадром   | guard against a giant frame
    if length > 1 << 30:
        raise ConnectionError('frame too large')
    payload = recv_exact(sock, length) if length else b''

    return ftype, payload


def write_frame(sock, ftype, payload):
    #* шлём одним куском, чтобы не рассыпать по сети | send in one piece, no scatter
    sock.sendall(pack_frame(ftype, payload))


#/ ----------------------------------------------------------------------------
#/  зашифрованные сообщения  |  encrypted messages
#/ ----------------------------------------------------------------------------

def pack_encrypted(aes_key, obj):
    #* json → байты → шифруем                     | json → bytes → encrypt
    plain = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    return pack_frame(FT_ENC_JSON, aes_encrypt(aes_key, plain))


def unpack_encrypted(aes_key, blob):
    #* шифротекст → json-объект                    | ciphertext → json object
    plain = aes_decrypt(aes_key, blob)

    return json.loads(plain.decode('utf-8'))


def pack_blob(aes_key, msg_id, index, total, chunk):
    #* собираем чанк: заголовок + данные, шифруем  | build chunk: header + data, encrypt
    head = BLOB_HEADER.pack(msg_id.encode('ascii'), index, total, len(chunk))
    return pack_frame(FT_ENC_BLOB, aes_encrypt(aes_key, head + chunk))


def unpack_blob(aes_key, blob):
    #* расшифровываем и разбираем заголовок чанка  | decrypt and parse the chunk header
    plain = aes_decrypt(aes_key, blob)
    mid, index, total, size = BLOB_HEADER.unpack_from(plain, 0)
    data = plain[BLOB_HEADER_SIZE:]

    return mid.decode('ascii'), index, total, data
