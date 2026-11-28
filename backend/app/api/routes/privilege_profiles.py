from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, enforce_csrf, require_admin, require_operator
from app.core.db import get_db
from app.models import AuthUser, Manufacturer, PrivilegeProfile, PrivilegeProfileAttr, SystemUser
from app.schemas.privilege_profile import (
    PrivilegeProfileCreate,
    PrivilegeProfileOut,
    PrivilegeProfileUpdate,
)
from app.services import audit, radius_sync, tacacs_sync

router = APIRouter(prefix="/privilege-profiles", tags=["privilege-profiles"])


def _to_out(p: PrivilegeProfile) -> PrivilegeProfileOut:
    return PrivilegeProfileOut(
        id=p.id, name=p.name, description=p.description, is_builtin=p.is_builtin,
        group_name=p.group_name,
        attrs=[
            {"id": a.id, "manufacturer_id": a.manufacturer_id, "attribute": a.attribute,
             "op": a.op, "value": a.value}
            for a in p.attrs
        ],
        tacacs_priv_level=p.tacacs_priv_level,
        tacacs_extra_avpairs=p.tacacs_extra_avpairs,
        tacacs_enable_level=p.tacacs_enable_level,
        tacacs_cmd_allow=p.tacacs_cmd_allow,
        created_at=p.created_at, updated_at=p.updated_at,
    )


def _audit_after(p: PrivilegeProfile) -> dict:
    return {"name": p.name, "attrs": len(p.attrs), "tacacs_priv_level": p.tacacs_priv_level,
            "tacacs_enable_level": p.tacacs_enable_level, "tacacs_cmd_allow": p.tacacs_cmd_allow}


def _validate_manufacturers(db: Session, attrs) -> None:
    ids = {a.manufacturer_id for a in attrs}
    if ids:
        found = set(db.execute(
            select(Manufacturer.id).where(Manufacturer.id.in_(ids))
        ).scalars())
        missing = ids - found
        if missing:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                f"fabricante(s) inexistente(s): {sorted(missing)}")


@router.get("", response_model=list[PrivilegeProfileOut], dependencies=[Depends(require_operator)])
def list_profiles(db: Session = Depends(get_db)) -> list[PrivilegeProfileOut]:
    rows = db.execute(select(PrivilegeProfile).order_by(PrivilegeProfile.name)).scalars()
    return [_to_out(p) for p in rows]


@router.post("", response_model=PrivilegeProfileOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(enforce_csrf)])
def create_profile(
    body: PrivilegeProfileCreate, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_admin),
) -> PrivilegeProfileOut:
    if db.execute(select(PrivilegeProfile).where(PrivilegeProfile.name == body.name)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "já existe perfil com esse nome")
    _validate_manufacturers(db, body.attrs)

    profile = PrivilegeProfile(
        name=body.name, description=body.description,
        tacacs_priv_level=body.tacacs_priv_level,
        tacacs_extra_avpairs=body.tacacs_extra_avpairs,
        tacacs_enable_level=body.tacacs_enable_level,
        tacacs_cmd_allow=body.tacacs_cmd_allow or None,
    )
    profile.attrs = [
        PrivilegeProfileAttr(manufacturer_id=a.manufacturer_id, attribute=a.attribute,
                             op=a.op, value=a.value)
        for a in body.attrs
    ]
    db.add(profile)
    db.flush()
    radius_sync.sync_profile_groupreply(db, profile)
    audit.record(db, action="create", entity_type="privilege_profile", entity_id=profile.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 after=_audit_after(profile))
    db.commit()
    # só depois do commit: o arquivo reflete o que está gravado
    tacacs_sync.regenerate(db)
    db.refresh(profile)
    return _to_out(profile)


@router.patch("/{profile_id}", response_model=PrivilegeProfileOut,
              dependencies=[Depends(enforce_csrf)])
def update_profile(
    profile_id: int, body: PrivilegeProfileUpdate, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_admin),
) -> PrivilegeProfileOut:
    profile = db.get(PrivilegeProfile, profile_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")

    old_name = profile.name
    if body.name and body.name != profile.name:
        if profile.is_builtin:
            raise HTTPException(status.HTTP_409_CONFLICT, "perfil interno não pode ser renomeado")
        if db.execute(select(PrivilegeProfile).where(PrivilegeProfile.name == body.name)).first():
            raise HTTPException(status.HTTP_409_CONFLICT, "já existe perfil com esse nome")
        profile.name = body.name
    if body.description is not None:
        profile.description = body.description
    if body.tacacs_priv_level is not None:
        profile.tacacs_priv_level = body.tacacs_priv_level
    if body.tacacs_extra_avpairs is not None:
        profile.tacacs_extra_avpairs = body.tacacs_extra_avpairs or None
    if "tacacs_enable_level" in body.model_fields_set:
        profile.tacacs_enable_level = body.tacacs_enable_level
    if body.tacacs_cmd_allow is not None:
        profile.tacacs_cmd_allow = body.tacacs_cmd_allow or None
    if body.attrs is not None:
        _validate_manufacturers(db, body.attrs)
        # Emite os DELETEs das linhas antigas antes de reinserir — senão o flush
        # tenta inserir um par (profile, manufacturer, attribute) que ainda existe
        # e bate na constraint uq_profile_attr.
        profile.attrs.clear()
        db.flush()
        profile.attrs = [
            PrivilegeProfileAttr(manufacturer_id=a.manufacturer_id, attribute=a.attribute,
                                 op=a.op, value=a.value)
            for a in body.attrs
        ]
    db.flush()

    if body.name and old_name != profile.name:
        radius_sync.rename_profile_group(db, old_name, profile.name)
    radius_sync.sync_profile_groupreply(db, profile)

    audit.record(db, action="update", entity_type="privilege_profile", entity_id=profile.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 after=_audit_after(profile))
    db.commit()
    # só depois do commit: o arquivo reflete o que está gravado
    tacacs_sync.regenerate(db)
    db.refresh(profile)
    return _to_out(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(enforce_csrf)])
def delete_profile(
    profile_id: int, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_admin),
) -> None:
    profile = db.get(PrivilegeProfile, profile_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")
    if profile.is_builtin:
        raise HTTPException(status.HTTP_409_CONFLICT, "perfil interno não pode ser removido")
    in_use = db.execute(
        select(func.count()).select_from(AuthUser).where(
            AuthUser.privilege_profile_id == profile_id
        )
    ).scalar_one()
    if in_use:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"perfil em uso por {in_use} usuário(s) de auth")

    group = profile.group_name
    db.delete(profile)
    db.flush()
    radius_sync.delete_profile_group(db, group)
    audit.record(db, action="delete", entity_type="privilege_profile", entity_id=profile_id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 before={"name": profile.name})
    db.commit()
    # só depois do commit: o arquivo reflete o que está gravado
    tacacs_sync.regenerate(db)
