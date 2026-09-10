from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_audit_reader
from app.core.db import get_db
from app.core.security import utcnow
from app.models import AuditLog, MfaTrustedDevice, SystemUser
from app.schemas.audit import AuditLogOut, TrustedDeviceRow
from app.schemas.common import Page

router = APIRouter(
    prefix="/audit", tags=["audit"], dependencies=[Depends(require_audit_reader)]
)


@router.get("/trusted-devices", response_model=list[TrustedDeviceRow])
def list_trusted_devices(db: Session = Depends(get_db)) -> list[TrustedDeviceRow]:
    """Dispositivos memorizados no 2FA de todos os utilizadores do painel."""
    now = utcnow()
    rows = db.execute(
        select(MfaTrustedDevice, SystemUser.username)
        .join(SystemUser, SystemUser.id == MfaTrustedDevice.system_user_id)
        .order_by(MfaTrustedDevice.created_at.desc())
    ).all()
    return [
        TrustedDeviceRow(
            id=d.id, username=uname, user_agent=d.user_agent, ip_address=d.ip_address,
            created_at=d.created_at, last_used_at=d.last_used_at,
            expires_at=d.expires_at, expired=d.expires_at <= now,
        )
        for d, uname in rows
    ]


@router.get("", response_model=Page[AuditLogOut])
def list_audit(
    db: Session = Depends(get_db),
    actor: str | None = None,
    entity_type: str | None = None,
    action: str | None = None,
    since: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> Page[AuditLogOut]:
    stmt = select(AuditLog)
    if actor:
        stmt = stmt.where(AuditLog.actor_username.like(f"%{actor}%"))
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if since:
        stmt = stmt.where(AuditLog.created_at >= since)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(AuditLog.created_at.desc())
        .limit(page_size).offset((page - 1) * page_size)
    ).scalars()
    return Page(items=[AuditLogOut.model_validate(r) for r in rows],
                total=total, page=page, page_size=page_size)
