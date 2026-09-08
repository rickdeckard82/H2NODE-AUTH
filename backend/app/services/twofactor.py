"""2FA (TOTP, RFC 6238) para utilizadores do painel."""

import pyotp
import segno

_ISSUER = "Pulse RADIUS"


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
