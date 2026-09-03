from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, enforce_csrf, require_superadmin
from app.core.db import get_db
from app.core.security import hash_password
from app.models import SystemRole, SystemUser
from app.schemas.common import Page
from app.schemas.system_user import SystemUserCreate, SystemUserOut, SystemUserUpdate
from app.services import audit

router = APIRouter(
    prefix="/system-users",
    tags=["system-users"],
    dependencies=[Depends(enforce_csrf)],
)


def _count_active_superadmins(db: Session, exclude_id: int | None = None) -> int:
    q = select(func.count()).select_from(SystemUser).where(
        SystemUser.role == SystemRole.superadmin, SystemUser.is_active.is_(True)
    )
    if exclude_id is not None:
        q = q.where(SystemUser.id != exclude_id)
    return db.execute(q).scalar_one()


@router.get("", response_model=Page[SystemUserOut])
def list_users(
    db: Session = Depends(get_db),
    _: SystemUser = Depends(require_superadmin),
    q: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> Page[SystemUserOut]:
    stmt = select(SystemUser)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(SystemUser.username.like(like), SystemUser.email.like(like),
                              SystemUser.full_name.like(like)))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(SystemUser.username).limit(page_size).offset((page - 1) * page_size)
    ).scalars()
    return Page(items=[SystemUserOut.model_validate(r) for r in rows],
                total=total, page=page, page_size=page_size)


@router.post("", response_model=SystemUserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: SystemUserCreate, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_superadmin),
) -> SystemUserOut:
    if db.execute(select(SystemUser).where(
        or_(SystemUser.username == body.username, SystemUser.email == body.email)
    )).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "username ou e-mail já em uso")
    user = SystemUser(
        username=body.username, email=body.email, full_name=body.full_name,
        role=body.role, is_active=body.is_active,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.flush()
    audit.record(db, action="create", entity_type="system_user", entity_id=user.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 after={"username": user.username, "role": user.role.value})
    db.commit()
    return SystemUserOut.model_validate(user)


@router.patch("/{user_id}", response_model=SystemUserOut)
def update_user(
    user_id: int, body: SystemUserUpdate, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_superadmin),
) -> SystemUserOut:
    user = db.get(SystemUser, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")

    before = {"role": user.role.value, "is_active": user.is_active, "email": user.email}
    demoting = (
        (body.role is not None and body.role != SystemRole.superadmin)
        or body.is_active is False
    )
    if user.role == SystemRole.superadmin and demoting and _count_active_superadmins(db, user.id) == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "não pode remover o último superadmin ativo")

    if body.email is not None:
        user.email = body.email
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password:
        user.password_hash = hash_password(body.password)

    audit.record(db, action="update", entity_type="system_user", entity_id=user.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 before=before,
                 after={"role": user.role.value, "is_active": user.is_active, "email": user.email})
    db.commit()
    return SystemUserOut.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_superadmin),
) -> None:
    if user_id == actor.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "não pode excluir a própria conta")
    user = db.get(SystemUser, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")
    if user.role == SystemRole.superadmin and _count_active_superadmins(db, user.id) == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "não pode excluir o último superadmin ativo")
    db.delete(user)
    audit.record(db, action="delete", entity_type="system_user", entity_id=user_id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 before={"username": user.username, "role": user.role.value})
    db.commit()
