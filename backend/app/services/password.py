"""Formatação de senha para o FreeRADIUS (usuários que autenticam nos equipamentos).

Usamos `SSHA2-512-Password`: base64( sha512(password || salt) || salt ).
O módulo `pap` do FreeRADIUS 3.2 valida esse formato nativamente, então a senha
nunca é gravada em texto claro. Como o login administrativo nos equipamentos é
PAP, isso é suficiente (CHAP/MS-CHAP exigiriam texto claro).
"""

import base64
import hashlib
import os

RADIUS_PASSWORD_ATTR = "SSHA2-512-Password"
_SALT_BYTES = 16


def make_ssha512(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(_SALT_BYTES)
    digest = hashlib.sha512(password.encode() + salt).digest()
    return base64.b64encode(digest + salt).decode()


def verify_ssha512(password: str, stored_b64: str) -> bool:
    raw = base64.b64decode(stored_b64)
    digest, salt = raw[:64], raw[64:]
    return hashlib.sha512(password.encode() + salt).digest() == digest
