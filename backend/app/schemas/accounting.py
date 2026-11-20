from pydantic import BaseModel

from app.schemas.common import UtcDatetime


class SessionOut(BaseModel):
    id: int
    username: str
    nasipaddress: str
    nas_name: str | None = None
    acctsessionid: str
    acctstarttime: UtcDatetime | None
    acctstoptime: UtcDatetime | None
    acctsessiontime: int | None
    acctinputoctets: int | None
    acctoutputoctets: int | None
    callingstationid: str
    acctterminatecause: str
    active: bool


class AuthEventOut(BaseModel):
    id: int
    username: str
    reply: str
    authdate: UtcDatetime
    accepted: bool
    protocol: str = "radius"
    source_ip: str | None = None
    dest_ip: str | None = None
    nas_name: str | None = None


class CommandEventOut(BaseModel):
    id: int
    event_time: UtcDatetime
    nasipaddress: str
    nas_name: str | None = None
    username: str
    callingstationid: str
    action: str
    command: str
    acctsessionid: str


class DailyPoint(BaseModel):
    date: str  # YYYY-MM-DD no fuso do operador
    accepts: int
    rejects: int
    sessions: int


class AccountingStats(BaseModel):
    active_sessions: int
    sessions_7d: int
    accepts_7d: int
    rejects_7d: int
    top_users_7d: list[dict]
    equipment_tacacs: int
    equipment_radius: int
    top_devices_7d: list[dict]
    # 7 pontos, do mais antigo ao mais recente (contando hoje).
    daily: list[DailyPoint]
