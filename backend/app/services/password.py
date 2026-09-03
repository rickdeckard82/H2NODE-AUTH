"""Formatação de senha para o FreeRADIUS (usuários que autenticam nos equipamentos).

Gravamos DOIS verificadores em `radcheck`, nenhum em texto claro:

- `SSHA2-512-Password`: base64( sha512(password || salt) || salt ). Usado pelo
  `pap` — Huawei / Juniper / Datacom fazem login administrativo via PAP.
- `NT-Password`: MD4( password em UTF-16LE ), hex. Usado pelo `mschap` — o login
  administrativo do MikroTik (Winbox/SSH/console) negocia MS-CHAPv2, que não
  valida contra hash SHA-512. MD4 é fraco, mas o hash não trafega e a senha
  continua fora do banco em claro.
"""

import base64
import hashlib
import os
import struct

RADIUS_PASSWORD_ATTR = "SSHA2-512-Password"
RADIUS_NT_PASSWORD_ATTR = "NT-Password"
_SALT_BYTES = 16


def make_ssha512(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(_SALT_BYTES)
    digest = hashlib.sha512(password.encode() + salt).digest()
    return base64.b64encode(digest + salt).decode()


def verify_ssha512(password: str, stored_b64: str) -> bool:
    raw = base64.b64decode(stored_b64)
    digest, salt = raw[:64], raw[64:]
    return hashlib.sha512(password.encode() + salt).digest() == digest


def make_nt_hash(password: str) -> str:
    """NT hash (MD4 do password em UTF-16LE), em hex minúsculo — atributo NT-Password."""
    return _md4(password.encode("utf-16-le")).hex()


def _md4(data: bytes) -> bytes:
    """MD4 (RFC 1320) puro em Python. O OpenSSL 3 não expõe `md4` por padrão,
    então não dá para usar hashlib aqui."""

    def lrot(x: int, n: int) -> int:
        x &= 0xFFFFFFFF
        return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF

    msg = bytearray(data)
    bit_len = (8 * len(data)) & 0xFFFFFFFFFFFFFFFF
    msg.append(0x80)
    while len(msg) % 64 != 56:
        msg.append(0)
    msg += struct.pack("<Q", bit_len)

    a, b, c, d = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476

    def f(x, y, z):
        return (x & y) | (~x & z)

    def g(x, y, z):
        return (x & y) | (x & z) | (y & z)

    def h(x, y, z):
        return x ^ y ^ z

    for off in range(0, len(msg), 64):
        x = list(struct.unpack("<16I", msg[off:off + 64]))
        aa, bb, cc, dd = a, b, c, d

        for k in range(0, 16, 4):
            a = lrot(a + f(b, c, d) + x[k], 3)
            d = lrot(d + f(a, b, c) + x[k + 1], 7)
            c = lrot(c + f(d, a, b) + x[k + 2], 11)
            b = lrot(b + f(c, d, a) + x[k + 3], 19)

        for k in range(4):
            a = lrot(a + g(b, c, d) + x[k] + 0x5A827999, 3)
            d = lrot(d + g(a, b, c) + x[k + 4] + 0x5A827999, 5)
            c = lrot(c + g(d, a, b) + x[k + 8] + 0x5A827999, 9)
            b = lrot(b + g(c, d, a) + x[k + 12] + 0x5A827999, 13)

        for k in (0, 2, 1, 3):
            a = lrot(a + h(b, c, d) + x[k] + 0x6ED9EBA1, 3)
            d = lrot(d + h(a, b, c) + x[k + 8] + 0x6ED9EBA1, 9)
            c = lrot(c + h(d, a, b) + x[k + 4] + 0x6ED9EBA1, 11)
            b = lrot(b + h(c, d, a) + x[k + 12] + 0x6ED9EBA1, 15)

        a = (a + aa) & 0xFFFFFFFF
        b = (b + bb) & 0xFFFFFFFF
        c = (c + cc) & 0xFFFFFFFF
        d = (d + dd) & 0xFFFFFFFF

    return struct.pack("<4I", a, b, c, d)
