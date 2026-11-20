"""2FA para usuários do painel: TOTP (RFC 6238) + códigos de recuperação
+ dispositivos confiáveis ("lembrar deste dispositivo")."""

import hashlib
import secrets
from datetime import timedelta

import pyotp
import segno

from app.core.config import settings
from app.core.security import hash_password, utcnow, verify_password
from app.models import MfaRecoveryCode, MfaTrustedDevice, SystemUser

_ISSUER = "H2NODE Auth"

# Códigos de recuperação: uso único, mostrados só na ativação. Alfabeto sem
# caracteres ambíguos (0/O, 1/I/L). 10 grupos de 5 => ~51 bits de entropia.
_RECOVERY_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_RECOVERY_COUNT = 10
_RECOVERY_LEN = 10  # dígitos antes de formatar como XXXXX-XXXXX


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, *, username: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=_ISSUER)


def qr_data_uri(otpauth_uri: str) -> str:
    """QR code do otpauth:// como data URI (SVG), para escanear no cadastro do 2FA."""
    return segno.make(otpauth_uri, error="m").svg_data_uri(scale=4, border=2)


def verify_code(secret: str, code: str) -> bool:
    code = code.strip().replace(" ", "")
    if not code.isdigit():
        return False
    # valid_window=1 tolera deriva de ±30s entre o relógio do servidor e do app.
    return pyotp.totp.TOTP(secret).verify(code, valid_window=1)


def _new_recovery_code() -> str:
    raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(_RECOVERY_LEN))
    return f"{raw[:5]}-{raw[5:]}"


def _normalize_recovery_code(code: str) -> str:
    return "".join(ch for ch in code.strip().upper() if ch in _RECOVERY_ALPHABET)


def issue_recovery_codes(user: SystemUser) -> list[str]:
    """Descarta os códigos anteriores do usuário e gera um lote novo.

    Retorna os códigos em claro (para exibir uma única vez); no banco fica só o
    hash. Mexe na coleção ORM — quem chama faz o commit.
    """
    user.mfa_recovery_codes.clear()  # delete-orphan remove os antigos no flush
    codes = [_new_recovery_code() for _ in range(_RECOVERY_COUNT)]
    for c in codes:
        user.mfa_recovery_codes.append(
            MfaRecoveryCode(code_hash=hash_password(_normalize_recovery_code(c)))
        )
    return codes


def discard_recovery_codes(user: SystemUser) -> None:
    user.mfa_recovery_codes.clear()


def consume_recovery_code(user: SystemUser, code: str) -> bool:
    """Confere `code` contra os códigos de recuperação não usados do usuário.

    Se coincidir, marca-o como usado (sem commit) e devolve True.
    """
    candidate = _normalize_recovery_code(code)
    if len(candidate) != _RECOVERY_LEN:
        return False
    for row in user.mfa_recovery_codes:
        if row.used_at is None and verify_password(candidate, row.code_hash):
            row.used_at = utcnow()
            return True
    return False


# --- Dispositivos confiáveis ("lembrar deste dispositivo") --------------------
#
# Token aleatório de 256 bits: entropia suficiente para guardar só o SHA-256
# (sem sal/Argon2 — não é senha e precisa de lookup por hash a cada login).


def hash_device_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def register_trusted_device(
    user: SystemUser, *, user_agent: str | None, ip_address: str | None
) -> tuple[str, MfaTrustedDevice]:
    """Cria a linha do dispositivo confiável e devolve (token em claro p/ o
    cookie, a linha). Sem commit — quem chama fecha a transação."""
    token = secrets.token_urlsafe(32)
    device = MfaTrustedDevice(
        token_hash=hash_device_token(token),
        user_agent=(user_agent or "")[:255] or None,
        ip_address=ip_address,
        expires_at=utcnow() + timedelta(days=settings.mfa_trusted_device_ttl_days),
    )
    user.mfa_trusted_devices.append(device)
    return token, device


def trusted_device_valid(user: SystemUser, token: str) -> bool:
    """True se `token` casa com um dispositivo confiável não expirado do
    usuário. Nesse caso renova o uso e estende a validade (janela deslizante)."""
    if not token:
        return False
    wanted = hash_device_token(token)
    now = utcnow()
    for dev in user.mfa_trusted_devices:
        if secrets.compare_digest(dev.token_hash, wanted) and dev.expires_at > now:
            dev.last_used_at = now
            dev.expires_at = now + timedelta(days=settings.mfa_trusted_device_ttl_days)
            return True
    return False


def discard_trusted_devices(user: SystemUser) -> int:
    """Remove todos os dispositivos confiáveis do usuário; devolve quantos."""
    n = len(user.mfa_trusted_devices)
    user.mfa_trusted_devices.clear()  # delete-orphan remove as linhas no flush
    return n
