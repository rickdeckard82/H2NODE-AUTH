from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, enforce_csrf, require_admin, require_operator
from app.core.db import get_db
from app.models import AuthUser, AuthUserGroup, PrivilegeProfile, SystemUser
from app.schemas.auth_user import (
    AuthUserCreate,
    AuthUserOut,
    AuthUserPasswordReset,
    AuthUserUpdate,
)
from app.schemas.common import Page
from app.services import audit, radius_sync

router = APIRouter(prefix="/auth-users", tags=["auth-users"])


def _to_out(u: AuthUser) -> AuthUserOut:
    return AuthUserOut(
        id=u.id, username=u.username, full_name=u.full_name, email=u.email,
        privilege_profile_id=u.privilege_profile_id, auth_group_id=u.auth_group_id,
        is_active=u.is_active, expires_at=u.expires_at, profile_name=u.profile.name,
        auth_group_name=u.auth_group.name if u.auth_group else None,
        last_auth_at=u.last_auth_at, created_at=u.created_at, updated_at=u.updated_at,
    )


def _get_profile(db: Session, pid: int) -> PrivilegeProfile:
    p = db.get(PrivilegeProfile, pid)
    if p is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "perfil de privilégio inexistente")
    return p


def _check_group(db: Session, gid: int) -> None:
    if db.get(AuthUserGroup, gid) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "grupo de usuário inexistente")


@router.get("", response_model=Page[AuthUserOut], dependencies=[Depends(require_operator)])
def list_auth_users(
    db: Session = Depends(get_db),
    q: str | None = None,
    profile_id: int | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> Page[AuthUserOut]:
    stmt = select(AuthUser)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(AuthUser.username.like(like), AuthUser.full_name.like(like),
                              AuthUser.email.like(like)))
    if profile_id is not None:
        stmt = stmt.where(AuthUser.privilege_profile_id == profile_id)
    if is_active is not None:
        stmt = stmt.where(AuthUser.is_active.is_(is_active))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(AuthUser.username).limit(page_size).offset((page - 1) * page_size)
    ).scalars()
    return Page(items=[_to_out(u) for u in rows], total=total, page=page, page_size=page_size)


@router.post("", response_model=AuthUserOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(enforce_csrf)])
def create_auth_user(
    body: AuthUserCreate, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_operator),
) -> AuthUserOut:
    username = body.username.lower()
    if db.execute(select(AuthUser).where(AuthUser.username == username)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "já existe usuário com esse login")
    _get_profile(db, body.privilege_profile_id)
    if body.auth_group_id:
        _check_group(db, body.auth_group_id)

    user = AuthUser(
        username=username, full_name=body.full_name, email=body.email,
        privilege_profile_id=body.privilege_profile_id,
        auth_group_id=body.auth_group_id or None, is_active=body.is_active,
        expires_at=body.expires_at, created_by=actor.id,
    )
    db.add(user)
    db.flush()
    radius_sync.sync_auth_user(db, user, password=body.password)
    audit.record(db, action="create", entity_type="auth_user", entity_id=user.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 after={"username": user.username, "profile_id": user.privilege_profile_id})
    db.commit()
    db.refresh(user)
    return _to_out(user)


@router.patch("/{user_id}", response_model=AuthUserOut, dependencies=[Depends(enforce_csrf)])
def update_auth_user(
    user_id: int, body: AuthUserUpdate, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_operator),
) -> AuthUserOut:
    user = db.get(AuthUser, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")
    before = {"profile_id": user.privilege_profile_id, "is_active": user.is_active}

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.email is not None:
        user.email = body.email
    if body.privilege_profile_id is not None:
        _get_profile(db, body.privilege_profile_id)
        user.privilege_profile_id = body.privilege_profile_id
    if body.auth_group_id is not None:
        if body.auth_group_id == 0:
            user.auth_group_id = None
        else:
            _check_group(db, body.auth_group_id)
            user.auth_group_id = body.auth_group_id
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.expires_at is not None:
        user.expires_at = body.expires_at
    db.flush()

    # re-sincroniza o grupo (perfil pode ter mudado); senha inalterada
    radius_sync.sync_auth_user(db, user, password=None)
    audit.record(db, action="update", entity_type="auth_user", entity_id=user.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 before=before,
                 after={"profile_id": user.privilege_profile_id, "is_active": user.is_active})
    db.commit()
    db.refresh(user)
    return _to_out(user)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=[Depends(enforce_csrf)])
def reset_password(
    user_id: int, body: AuthUserPasswordReset, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_operator),
) -> None:
    user = db.get(AuthUser, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")
    radius_sync.sync_auth_user(db, user, password=body.password)
    audit.record(db, action="reset_password", entity_type="auth_user", entity_id=user.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request))
    db.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(enforce_csrf)])
def delete_auth_user(
    user_id: int, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_admin),
) -> None:
    user = db.get(AuthUser, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")
    username = user.username
    db.delete(user)
    radius_sync.delete_auth_user(db, username)
    audit.record(db, action="delete", entity_type="auth_user", entity_id=user_id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 before={"username": username})
    db.commit()
