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
    last_login_at: UtcDatetime | None


class SessionOut(BaseModel):
    user: MeOut
    csrf_token: str
