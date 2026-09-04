from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import UtcDatetime


class SmtpSettingsIn(BaseModel):
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=587, ge=1, le=65535)
    username: str | None = Field(default=None, max_length=255)
    # Em branco em uma atualização = mantém a senha já guardada.
    password: str | None = Field(default=None, max_length=255)
    clear_password: bool = False
    use_tls: bool = True
    use_ssl: bool = False
    from_email: EmailStr
    from_name: str | None = Field(default=None, max_length=190)


class SmtpSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    host: str
    port: int
    username: str | None
    has_password: bool
    use_tls: bool
    use_ssl: bool
    from_email: str
    from_name: str | None
    updated_at: UtcDatetime


class SmtpTestIn(BaseModel):
    to: EmailStr
