from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import (
    client_ip,
    enforce_csrf,
    require_admin,
    require_auditor,
    require_operator,
)
from app.core.db import get_db
from app.models import Equipment, Site, SystemUser
from app.schemas.site import SiteCreate, SiteOut, SiteUpdate
from app.services import audit

router = APIRouter(prefix="/sites", tags=["sites"])


def _count(db: Session, name: str) -> int:
    return db.execute(
        select(func.count()).select_from(Equipment).where(Equipment.site == name)
    ).scalar_one()


def _out(db: Session, s: Site) -> SiteOut:
    return SiteOut(id=s.id, name=s.name, description=s.description,
                   equipment_count=_count(db, s.name),
                   created_at=s.created_at, updated_at=s.updated_at)


@router.get("", response_model=list[SiteOut], dependencies=[Depends(require_auditor)])
def list_sites(db: Session = Depends(get_db)) -> list[SiteOut]:
    counts = dict(db.execute(
        select(Equipment.site, func.count()).where(Equipment.site.is_not(None))
        .group_by(Equipment.site)
    ).all())
    rows = db.execute(select(Site).order_by(Site.name)).scalars()
    return [SiteOut(id=s.id, name=s.name, description=s.description,
                    equipment_count=counts.get(s.name, 0),
                    created_at=s.created_at, updated_at=s.updated_at) for s in rows]


@router.post("", response_model=SiteOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(enforce_csrf)])
def create_site(
    body: SiteCreate, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_operator),
) -> SiteOut:
    name = body.name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "nome obrigatório")
    if db.execute(select(Site).where(Site.name == name)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "já existe site com esse nome")
    s = Site(name=name, description=body.description)
    db.add(s)
    db.flush()
    audit.record(db, action="create", entity_type="site", entity_id=s.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 after={"name": s.name})
    db.commit()
    return _out(db, s)


@router.patch("/{site_id}", response_model=SiteOut, dependencies=[Depends(enforce_csrf)])
def update_site(
    site_id: int, body: SiteUpdate, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_operator),
) -> SiteOut:
    s = db.get(Site, site_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")
    before = {"name": s.name, "description": s.description}
    old_name = s.name
    if body.name is not None:
        new = body.name.strip()
        if not new:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "nome obrigatório")
        if new != old_name:
            if db.execute(select(Site).where(Site.name == new)).first():
                raise HTTPException(status.HTTP_409_CONFLICT, "já existe site com esse nome")
            s.name = new
            # Equipment.site guarda o nome: acompanha a renomeação.
            db.execute(update(Equipment).where(Equipment.site == old_name).values(site=new))
    if body.description is not None:
        s.description = body.description or None
    db.flush()
    audit.record(db, action="update", entity_type="site", entity_id=s.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 before=before, after={"name": s.name, "description": s.description})
    db.commit()
    return _out(db, s)


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(enforce_csrf)])
def delete_site(
    site_id: int, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_admin),
) -> None:
    s = db.get(Site, site_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")
    n = _count(db, s.name)
    if n:
        raise HTTPException(status.HTTP_409_CONFLICT, f"site em uso por {n} equipamento(s)")
    name = s.name
    db.delete(s)
    audit.record(db, action="delete", entity_type="site", entity_id=site_id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 before={"name": name})
    db.commit()
