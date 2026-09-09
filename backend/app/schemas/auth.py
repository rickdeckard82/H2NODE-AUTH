from pydantic import BaseModel, ConfigDict, Field

from app.models.system_user import SystemRole
from app.schemas.common import UtcDatetime


class LoginIn(BaseModel):
    username: str
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)


class InviteOut(BaseModel):
    username: str
    email: str
    full_name: str


class AcceptInviteIn(BaseModel):
    token: str
    password: str = Field(min_length=10, max_length=128)


class MeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str
    role: SystemRole
    is_active: bool
    timezone: str
    mfa_enabled: bool
    mfa_recovery_codes_remaining: int = 0
    last_login_at: UtcDatetime | None


class SessionOut(BaseModel):
    # Login concluído.
    user: MeOut | None = None
    csrf_token: str | None = None
    # 2ª etapa exigida: enviar `mfa_token` + código para /auth/mfa/verify.
    mfa_required: bool = False
    mfa_token: str | None = None


# Aceita um TOTP de 6 dígitos OU um código de recuperação (XXXXX-XXXXX).
_MfaOrRecovery = Field(min_length=6, max_length=32)


class MfaVerifyIn(BaseModel):
    mfa_token: str
    code: str = _MfaOrRecovery


class MfaSetupOut(BaseModel):
    secret: str
    otpauth_uri: str
    qr_svg: str  # data URI (image/svg+xml) do QR code do otpauth_uri


class MfaCodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class MfaDisableIn(BaseModel):
    password: str
    code: str = _MfaOrRecovery


class MfaRegenerateIn(BaseModel):
    password: str
    code: str = _MfaOrRecovery


class MfaEnableOut(BaseModel):
    detail: str
    recovery_codes: list[str]


class RecoveryCodesOut(BaseModel):
    recovery_codes: list[str]
