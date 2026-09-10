from typing import Literal
from zoneinfo import available_timezones

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.system_user import SystemRole
from app.schemas.common import UtcDatetime

_TZS = available_timezones()

Language = Literal["pt-BR", "en-US"]


def _check_tz(v: str | None) -> str | None:
    if v is not None and v not in _TZS:
        raise ValueError(f"fuso horário inválido: {v!r} (use um nome IANA, ex.: America/Sao_Paulo)")
    return v


class SystemUserBase(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=190)
    role: SystemRole = SystemRole.operator
    is_active: bool = True
    timezone: str = Field(default="America/Sao_Paulo", max_length=64)
    language: Language = "pt-BR"

    _v_tz = field_validator("timezone")(_check_tz)


class SystemUserCreate(SystemUserBase):
    # Em branco => envia convite por e-mail para o usuário criar a própria senha
    # (requer SMTP configurado em Configurações).
    password: str | None = Field(default=None, min_length=10, max_length=128)


class SystemUserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=190)
    role: SystemRole | None = None
    is_active: bool | None = None
    timezone: str | None = Field(default=None, max_length=64)
    language: Language | None = None
    password: str | None = Field(default=None, min_length=10, max_length=128)

    _v_tz = field_validator("timezone")(_check_tz)


class SystemUserOut(SystemUserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    has_password: bool
    mfa_enabled: bool
    last_login_at: UtcDatetime | None
    created_at: UtcDatetime
    updated_at: UtcDatetime
