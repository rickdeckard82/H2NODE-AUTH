from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, enforce_csrf, require_auditor, require_operator
from app.core.crypto import encrypt
from app.core.db import get_db
from app.models import Equipment, Manufacturer, SystemUser
from app.schemas.common import Page
from app.schemas.equipment import EquipmentCreate, EquipmentOut, EquipmentUpdate
from app.services import audit, radius_sync

router = APIRouter(prefix="/equipment", tags=["equipment"])


def _secret_source(eq: Equipment) -> str:
    if eq.radius_secret_enc:
        return "equipment"
    if eq.manufacturer and eq.manufacturer.radius_secret_enc:
        return "manufacturer"
    return "none"


def _to_out(eq: Equipment) -> EquipmentOut:
    return EquipmentOut(
        id=eq.id, name=eq.name, mgmt_ip=eq.mgmt_ip, manufacturer_id=eq.manufacturer_id,
        model=eq.model, site=eq.site, shortname=eq.shortname, coa_port=eq.coa_port,
        status=eq.status, description=eq.description,
        manufacturer_name=eq.manufacturer.name, manufacturer_display=eq.manufacturer.display_name,
        vendor_kind=eq.manufacturer.vendor_kind,
        has_own_secret=bool(eq.radius_secret_enc), secret_source=_secret_source(eq),
        last_seen_at=eq.last_seen_at, created_at=eq.created_at, updated_at=eq.updated_at,
    )


def _get_manufacturer(db: Session, mid: int) -> Manufacturer:
    m = db.get(Manufacturer, mid)
    if m is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "fabricante inexistente")
    return m


@router.get("", response_model=Page[EquipmentOut], dependencies=[Depends(require_auditor)])
def list_equipment(
    db: Session = Depends(get_db),
    manufacturer_id: int | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> Page[EquipmentOut]:
    stmt = select(Equipment).join(Manufacturer)
    if manufacturer_id is not None:
        stmt = stmt.where(Equipment.manufacturer_id == manufacturer_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Equipment.name.like(like), Equipment.mgmt_ip.like(like),
                              Equipment.shortname.like(like), Equipment.site.like(like)))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(Equipment.name).limit(page_size).offset((page - 1) * page_size)
    ).scalars()
    return Page(items=[_to_out(e) for e in rows], total=total, page=page, page_size=page_size)


@router.get("/{equipment_id}", response_model=EquipmentOut, dependencies=[Depends(require_auditor)])
def get_equipment(equipment_id: int, db: Session = Depends(get_db)) -> EquipmentOut:
    eq = db.get(Equipment, equipment_id)
    if eq is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")
    return _to_out(eq)


@router.post("", response_model=EquipmentOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(enforce_csrf)])
def create_equipment(
    body: EquipmentCreate, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_operator),
) -> EquipmentOut:
    if db.execute(select(Equipment).where(Equipment.mgmt_ip == body.mgmt_ip)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "já existe equipamento com esse IP de gerência")
    manufacturer = _get_manufacturer(db, body.manufacturer_id)
    if not body.radius_secret and not manufacturer.radius_secret_enc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"informe o segredo RADIUS ou cadastre um segredo padrão no fabricante "
            f"'{manufacturer.name}'",
        )

    eq = Equipment(
        name=body.name, mgmt_ip=body.mgmt_ip, manufacturer_id=body.manufacturer_id,
        model=body.model, site=body.site, shortname=body.shortname, coa_port=body.coa_port,
        status=body.status, description=body.description,
        radius_secret_enc=encrypt(body.radius_secret) if body.radius_secret else None,
        created_by=actor.id,
    )
    db.add(eq)
    db.flush()
    radius_sync.sync_equipment(db, eq, manufacturer=manufacturer)
    audit.record(db, action="create", entity_type="equipment", entity_id=eq.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 after={"name": eq.name, "mgmt_ip": eq.mgmt_ip, "manufacturer": manufacturer.name,
                        "secret_source": _secret_source(eq)})
    db.commit()
    db.refresh(eq)
    return _to_out(eq)


@router.patch("/{equipment_id}", response_model=EquipmentOut, dependencies=[Depends(enforce_csrf)])
def update_equipment(
    equipment_id: int, body: EquipmentUpdate, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_operator),
) -> EquipmentOut:
    eq = db.get(Equipment, equipment_id)
    if eq is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")

    old_ip = eq.mgmt_ip
    before = {"name": eq.name, "mgmt_ip": eq.mgmt_ip, "status": eq.status.value,
              "secret_source": _secret_source(eq)}

    if body.mgmt_ip and body.mgmt_ip != eq.mgmt_ip:
        if db.execute(select(Equipment).where(Equipment.mgmt_ip == body.mgmt_ip)).first():
            raise HTTPException(status.HTTP_409_CONFLICT, "IP de gerência já em uso")
        eq.mgmt_ip = body.mgmt_ip
    for field in ("name", "model", "site", "shortname", "coa_port", "status", "description"):
        val = getattr(body, field)
        if val is not None:
            setattr(eq, field, val)
    if body.manufacturer_id is not None:
        _get_manufacturer(db, body.manufacturer_id)
        eq.manufacturer_id = body.manufacturer_id
    if body.inherit_secret:
        eq.radius_secret_enc = None
    elif body.radius_secret:
        eq.radius_secret_enc = encrypt(body.radius_secret)
    db.flush()
    db.refresh(eq)

    radius_sync.rename_equipment_nas(db, old_ip, eq.mgmt_ip)
    radius_sync.sync_equipment(db, eq, manufacturer=eq.manufacturer)
    audit.record(db, action="update", entity_type="equipment", entity_id=eq.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 before=before,
                 after={"name": eq.name, "mgmt_ip": eq.mgmt_ip, "status": eq.status.value,
                        "secret_source": _secret_source(eq)})
    db.commit()
    db.refresh(eq)
    return _to_out(eq)


@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(enforce_csrf)])
def delete_equipment(
    equipment_id: int, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_operator),
) -> None:
    eq = db.get(Equipment, equipment_id)
    if eq is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")
    ip, name = eq.mgmt_ip, eq.name
    db.delete(eq)
    radius_sync.delete_equipment_nas(db, ip)
    audit.record(db, action="delete", entity_type="equipment", entity_id=equipment_id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 before={"name": name, "mgmt_ip": ip})
    db.commit()
