from datetime import datetime

from pydantic import BaseModel


class SessionOut(BaseModel):
    id: int
    username: str
    nasipaddress: str
    nas_name: str | None = None
    acctsessionid: str
    acctstarttime: datetime | None
    acctstoptime: datetime | None
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
    authdate: datetime
    accepted: bool


class AccountingStats(BaseModel):
    active_sessions: int
    sessions_last_24h: int
    accepts_last_24h: int
    rejects_last_24h: int
    top_users_24h: list[dict]
