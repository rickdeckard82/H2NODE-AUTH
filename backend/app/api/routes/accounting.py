import csv
import io
import re
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_auditor
from app.core.db import get_db
from app.models import CmdAcct, Equipment, RadAcct, RadPostAuth
from app.schemas.accounting import (
    AccountingStats,
    AuthEventOut,
    CommandEventOut,
    SessionOut,
)
from app.schemas.common import Page

router = APIRouter(
    prefix="/accounting", tags=["accounting"], dependencies=[Depends(require_auditor)]
)


def _nas_names(db: Session) -> dict[str, str]:
    return dict(db.execute(select(Equipment.mgmt_ip, Equipment.name)).all())  # type: ignore[arg-type]


_ESC_RE = re.compile(r"=([0-9A-Fa-f]{2})")


def _unescape(s: str | None) -> str:
    """Reverte o escape '=XX' que o rlm_sql aplica a chars fora de safe_characters
    (o site `default` grava o comando via %{sql:...})."""
    return _ESC_RE.sub(lambda m: chr(int(m.group(1), 16)), s or "")


def _session_stmt(
    username: str | None, nas_ip: str | None, active: bool | None,
    since: datetime | None, until: datetime | None,
):
    stmt = select(RadAcct)
    if username:
        stmt = stmt.where(RadAcct.username.like(f"%{username}%"))
    if nas_ip:
        stmt = stmt.where(RadAcct.nasipaddress == nas_ip)
    if active is True:
        stmt = stmt.where(RadAcct.acctstoptime.is_(None))
    elif active is False:
        stmt = stmt.where(RadAcct.acctstoptime.is_not(None))
    if since:
        stmt = stmt.where(RadAcct.acctstarttime >= since)
    if until:
        stmt = stmt.where(RadAcct.acctstarttime <= until)
    return stmt


@router.get("/sessions", response_model=Page[SessionOut])
def list_sessions(
    db: Session = Depends(get_db),
    username: str | None = None,
    nas_ip: str | None = None,
    active: bool | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> Page[SessionOut]:
    stmt = _session_stmt(username, nas_ip, active, since, until)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(RadAcct.acctstarttime.desc())
        .limit(page_size).offset((page - 1) * page_size)
    ).scalars()

    nas_names = _nas_names(db)
    items = [
        SessionOut(
            id=r.radacctid, username=r.username, nasipaddress=r.nasipaddress,
            nas_name=nas_names.get(r.nasipaddress),
            acctsessionid=r.acctsessionid, acctstarttime=r.acctstarttime,
            acctstoptime=r.acctstoptime, acctsessiontime=r.acctsessiontime,
            acctinputoctets=r.acctinputoctets, acctoutputoctets=r.acctoutputoctets,
            callingstationid=r.callingstationid, acctterminatecause=r.acctterminatecause,
            active=r.acctstoptime is None,
        )
        for r in rows
    ]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/sessions.csv")
def export_sessions_csv(
    db: Session = Depends(get_db),
    username: str | None = None,
    nas_ip: str | None = None,
    active: bool | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> StreamingResponse:
    stmt = _session_stmt(username, nas_ip, active, since, until).order_by(
        RadAcct.acctstarttime.desc()
    ).limit(50000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["username", "nas_ip", "session_id", "start", "stop", "duration_s",
                "in_octets", "out_octets", "calling_station", "terminate_cause"])
    for r in db.execute(stmt).scalars():
        w.writerow([r.username, r.nasipaddress, r.acctsessionid, r.acctstarttime,
                    r.acctstoptime, r.acctsessiontime, r.acctinputoctets,
                    r.acctoutputoctets, r.callingstationid, r.acctterminatecause])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sessions.csv"},
    )


# ─────────────────────────── Authentication (radpostauth) ───────────────────────────
def _authn_stmt(username: str | None, accepted: bool | None,
                since: datetime | None, until: datetime | None):
    stmt = select(RadPostAuth)
    if username:
        stmt = stmt.where(RadPostAuth.username.like(f"%{username}%"))
    if accepted is True:
        stmt = stmt.where(RadPostAuth.reply.like("Access-Accept%"))
    elif accepted is False:
        stmt = stmt.where(or_(RadPostAuth.reply.like("Access-Reject%"),
                              RadPostAuth.reply == ""))
    if since:
        stmt = stmt.where(RadPostAuth.authdate >= since)
    if until:
        stmt = stmt.where(RadPostAuth.authdate <= until)
    return stmt


@router.get("/authentication", response_model=Page[AuthEventOut])
@router.get("/auth-events", response_model=Page[AuthEventOut])  # alias legado (dashboard)
def list_authentication(
    db: Session = Depends(get_db),
    username: str | None = None,
    accepted: bool | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> Page[AuthEventOut]:
    stmt = _authn_stmt(username, accepted, since, until)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(RadPostAuth.authdate.desc())
        .limit(page_size).offset((page - 1) * page_size)
    ).scalars()
    items = [
        AuthEventOut(id=r.id, username=r.username, reply=r.reply, authdate=r.authdate,
                     accepted=r.reply.startswith("Access-Accept"))
        for r in rows
    ]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/authentication.csv")
def export_authentication_csv(
    db: Session = Depends(get_db),
    username: str | None = None,
    accepted: bool | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> StreamingResponse:
    stmt = _authn_stmt(username, accepted, since, until).order_by(
        RadPostAuth.authdate.desc()
    ).limit(50000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["authdate_utc", "username", "reply"])
    for r in db.execute(stmt).scalars():
        w.writerow([r.authdate, r.username, r.reply])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=authentication.csv"},
    )


# ───────────────── Comandos (cmd_acct) — Authorization / Accounting ─────────────────
def _cmd_stmt(username: str | None, nas_ip: str | None, action: str | None,
              since: datetime | None, until: datetime | None):
    stmt = select(CmdAcct)
    if username:
        stmt = stmt.where(CmdAcct.username.like(f"%{username}%"))
    if nas_ip:
        stmt = stmt.where(CmdAcct.nasipaddress == nas_ip)
    if action:
        stmt = stmt.where(CmdAcct.action == action)
    if since:
        stmt = stmt.where(CmdAcct.event_time >= since)
    if until:
        stmt = stmt.where(CmdAcct.event_time <= until)
    return stmt


@router.get("/commands", response_model=Page[CommandEventOut])
def list_commands(
    db: Session = Depends(get_db),
    username: str | None = None,
    nas_ip: str | None = None,
    action: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> Page[CommandEventOut]:
    stmt = _cmd_stmt(username, nas_ip, action, since, until)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(CmdAcct.event_time.desc())
        .limit(page_size).offset((page - 1) * page_size)
    ).scalars()
    nas_names = _nas_names(db)
    items = [
        CommandEventOut(
            id=r.id, event_time=r.event_time, nasipaddress=r.nasipaddress,
            nas_name=nas_names.get(r.nasipaddress), username=_unescape(r.username),
            callingstationid=r.callingstationid, action=r.action,
            command=_unescape(r.command), acctsessionid=r.acctsessionid,
        )
        for r in rows
    ]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/commands.csv")
def export_commands_csv(
    db: Session = Depends(get_db),
    username: str | None = None,
    nas_ip: str | None = None,
    action: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> StreamingResponse:
    stmt = _cmd_stmt(username, nas_ip, action, since, until).order_by(
        CmdAcct.event_time.desc()
    ).limit(50000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["event_time_utc", "nas_ip", "username", "source_ip", "action", "command"])
    for r in db.execute(stmt).scalars():
        w.writerow([r.event_time, r.nasipaddress, _unescape(r.username),
                    r.callingstationid, r.action, _unescape(r.command)])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=commands.csv"},
    )


@router.get("/stats", response_model=AccountingStats)
def stats(db: Session = Depends(get_db)) -> AccountingStats:
    now = datetime.now(UTC).replace(tzinfo=None)
    day_ago = now - timedelta(hours=24)

    active = db.execute(
        select(func.count()).select_from(RadAcct).where(RadAcct.acctstoptime.is_(None))
    ).scalar_one()
    last24 = db.execute(
        select(func.count()).select_from(RadAcct).where(RadAcct.acctstarttime >= day_ago)
    ).scalar_one()
    accepts = db.execute(
        select(func.count()).select_from(RadPostAuth).where(
            RadPostAuth.authdate >= day_ago, RadPostAuth.reply.like("Access-Accept%")
        )
    ).scalar_one()
    rejects = db.execute(
        select(func.count()).select_from(RadPostAuth).where(
            RadPostAuth.authdate >= day_ago,
            or_(RadPostAuth.reply.like("Access-Reject%"), RadPostAuth.reply == ""),
        )
    ).scalar_one()
    top = db.execute(
        select(RadAcct.username, func.count().label("n"))
        .where(RadAcct.acctstarttime >= day_ago)
        .group_by(RadAcct.username).order_by(func.count().desc()).limit(5)
    ).all()

    return AccountingStats(
        active_sessions=active, sessions_last_24h=last24,
        accepts_last_24h=accepts, rejects_last_24h=rejects,
        top_users_24h=[{"username": u, "sessions": n} for u, n in top],
    )
