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


class AccountingStats(BaseModel):
    active_sessions: int
    sessions_last_24h: int
    accepts_last_24h: int
    rejects_last_24h: int
    top_users_24h: list[dict]
