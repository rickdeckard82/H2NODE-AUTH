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
    last_login_at: UtcDatetime | None


class SessionOut(BaseModel):
    # Login concluído.
    user: MeOut | None = None
    csrf_token: str | None = None
    # 2ª etapa exigida: enviar `mfa_token` + código para /auth/mfa/verify.
    mfa_required: bool = False
    mfa_token: str | None = None


class MfaVerifyIn(BaseModel):
    mfa_token: str
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class MfaSetupOut(BaseModel):
    secret: str
    otpauth_uri: str


class MfaCodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class MfaDisableIn(BaseModel):
    password: str
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
