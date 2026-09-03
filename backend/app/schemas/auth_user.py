from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AuthUserBase(BaseModel):
    username: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9._@-]+$")
    full_name: str | None = Field(default=None, max_length=190)
    email: EmailStr | None = None
    privilege_profile_id: int
    auth_group_id: int | None = None
    is_active: bool = True
    expires_at: datetime | None = None


class AuthUserCreate(AuthUserBase):
    password: str = Field(min_length=12, max_length=128)


class AuthUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=190)
    email: EmailStr | None = None
    privilege_profile_id: int | None = None
    # None no corpo = não mexe; para desvincular, envie 0
    auth_group_id: int | None = None
    is_active: bool | None = None
    expires_at: datetime | None = None


class AuthUserPasswordReset(BaseModel):
    password: str = Field(min_length=12, max_length=128)


class AuthUserOut(AuthUserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_name: str
    auth_group_name: str | None
    last_auth_at: datetime | None
    created_at: datetime
    updated_at: datetime
