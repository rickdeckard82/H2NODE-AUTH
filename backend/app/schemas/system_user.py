from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.system_user import SystemRole


class SystemUserBase(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=190)
    role: SystemRole = SystemRole.operator
    is_active: bool = True


class SystemUserCreate(SystemUserBase):
    password: str = Field(min_length=10, max_length=128)


class SystemUserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=190)
    role: SystemRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=10, max_length=128)


class SystemUserOut(SystemUserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
