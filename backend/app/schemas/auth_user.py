from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.common import UtcDatetime


def _naive_utc(v: datetime | None) -> datetime | None:
    """O banco guarda UTC sem fuso (o RADIUS compara com NOW() do MySQL em UTC)."""
    if v is not None and v.tzinfo is not None:
        v = v.astimezone(UTC).replace(tzinfo=None)
    return v


class AuthUserBase(BaseModel):
    username: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9._@-]+$")
    full_name: str | None = Field(default=None, max_length=190)
    email: EmailStr | None = None
    privilege_profile_id: int
    auth_group_id: int | None = None
    is_active: bool = True
    expires_at: datetime | None = None

    _expires_utc = field_validator("expires_at")(_naive_utc)


class AuthUserCreate(AuthUserBase):
    password: str = Field(min_length=12, max_length=128)


class AuthUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=190)
    email: EmailStr | None = None
    privilege_profile_id: int | None = None
    # None no corpo = não mexe; para desvincular, envie 0
    auth_group_id: int | None = None
    is_active: bool | None = None
    # ausente = não mexe; null = remove (vale para expires_at e email)
    expires_at: datetime | None = None

    _expires_utc = field_validator("expires_at")(_naive_utc)


class AuthUserPasswordReset(BaseModel):
    password: str = Field(min_length=12, max_length=128)


class AuthUserOut(AuthUserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_name: str
    auth_group_name: str | None
    expires_at: UtcDatetime | None = None
    last_auth_at: UtcDatetime | None
    created_at: UtcDatetime
    updated_at: UtcDatetime
