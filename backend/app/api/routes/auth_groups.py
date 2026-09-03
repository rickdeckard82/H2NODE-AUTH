from ipaddress import ip_network

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, enforce_csrf, require_auditor, require_operator
from app.core.db import get_db
from app.models import AuthGroupCidr, AuthUser, AuthUserGroup, SystemUser
from app.schemas.auth_group import AuthGroupCreate, AuthGroupOut, AuthGroupUpdate, CidrIn
from app.services import audit

router = APIRouter(prefix="/auth-groups", tags=["auth-groups"])


def _member_counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(AuthUser.auth_group_id, func.count())
        .where(AuthUser.auth_group_id.is_not(None))
        .group_by(AuthUser.auth_group_id)
    ).all()
    return dict(rows)  # type: ignore[arg-type]


def _build_cidrs(items: list[CidrIn]) -> list[AuthGroupCidr]:
    out: list[AuthGroupCidr] = []
    for it in items:
        net = ip_network(it.cidr, strict=False)  # já normalizado no schema
        out.append(
            AuthGroupCidr(
                cidr=str(net),
                family=net.version,
                ip_start=net.network_address.packed,
                ip_end=net.broadcast_address.packed,
                note=it.note,
            )
        )
    return out


def _to_out(g: AuthUserGroup, members: int) -> AuthGroupOut:
    return AuthGroupOut(
        id=g.id, name=g.name, description=g.description,
        cidrs=[
            {"id": c.id, "cidr": c.cidr, "family": c.family, "note": c.note}
            for c in g.cidrs
        ],
        member_count=members, created_at=g.created_at, updated_at=g.updated_at,
    )


@router.get("", response_model=list[AuthGroupOut], dependencies=[Depends(require_auditor)])
def list_groups(db: Session = Depends(get_db)) -> list[AuthGroupOut]:
    counts = _member_counts(db)
    rows = db.execute(select(AuthUserGroup).order_by(AuthUserGroup.name)).scalars()
    return [_to_out(g, counts.get(g.id, 0)) for g in rows]


@router.post("", response_model=AuthGroupOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(enforce_csrf)])
def create_group(
    body: AuthGroupCreate, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_operator),
) -> AuthGroupOut:
    if db.execute(select(AuthUserGroup).where(AuthUserGroup.name == body.name)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "já existe grupo com esse nome")
    g = AuthUserGroup(name=body.name, description=body.description)
    g.cidrs = _build_cidrs(body.cidrs)
    db.add(g)
    db.flush()
    audit.record(db, action="create", entity_type="auth_group", entity_id=g.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 after={"name": g.name, "cidrs": [c.cidr for c in g.cidrs]})
    db.commit()
    db.refresh(g)
    return _to_out(g, 0)


@router.patch("/{group_id}", response_model=AuthGroupOut, dependencies=[Depends(enforce_csrf)])
def update_group(
    group_id: int, body: AuthGroupUpdate, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_operator),
) -> AuthGroupOut:
    g = db.get(AuthUserGroup, group_id)
    if g is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")
    if body.name and body.name != g.name:
        if db.execute(select(AuthUserGroup).where(AuthUserGroup.name == body.name)).first():
            raise HTTPException(status.HTTP_409_CONFLICT, "já existe grupo com esse nome")
        g.name = body.name
    if body.description is not None:
        g.description = body.description
    if body.cidrs is not None:
        g.cidrs = _build_cidrs(body.cidrs)
    db.flush()
    audit.record(db, action="update", entity_type="auth_group", entity_id=g.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 after={"name": g.name, "cidrs": [c.cidr for c in g.cidrs]})
    db.commit()
    db.refresh(g)
    return _to_out(g, _member_counts(db).get(g.id, 0))


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(enforce_csrf)])
def delete_group(
    group_id: int, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_operator),
) -> None:
    g = db.get(AuthUserGroup, group_id)
    if g is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")
    members = _member_counts(db).get(group_id, 0)
    if members:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"grupo com {members} usuário(s) — desvincule antes de remover")
    name = g.name
    db.delete(g)
    audit.record(db, action="delete", entity_type="auth_group", entity_id=group_id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 before={"name": name})
    db.commit()
