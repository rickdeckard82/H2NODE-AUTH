from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.system_user import SystemRole


class LoginIn(BaseModel):
    username: str
    password: str


class MeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str
    role: SystemRole
    is_active: bool
    last_login_at: datetime | None


class SessionOut(BaseModel):
    user: MeOut
    csrf_token: str
