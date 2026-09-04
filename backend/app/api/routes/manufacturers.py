from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, enforce_csrf, require_admin, require_auditor
from app.core.crypto import decrypt, encrypt
from app.core.db import get_db
from app.models import Equipment, Manufacturer, PrivilegeProfileAttr, SystemUser
from app.schemas.manufacturer import (
    ManufacturerCreate,
    ManufacturerOut,
    ManufacturerSecretOut,
    ManufacturerUpdate,
)
from app.services import audit, radius_sync, tacacs_sync

router = APIRouter(prefix="/manufacturers", tags=["manufacturers"])


def _counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(Equipment.manufacturer_id, func.count()).group_by(Equipment.manufacturer_id)
    ).all()
    return dict(rows)  # type: ignore[arg-type]


def _to_out(m: Manufacturer, eq_count: int) -> ManufacturerOut:
    return ManufacturerOut(
        id=m.id, name=m.name, display_name=m.display_name, vendor_kind=m.vendor_kind,
        radius_vendor_id=m.radius_vendor_id, aaa_protocol=m.aaa_protocol, notes=m.notes,
        has_secret=bool(m.radius_secret_enc), has_tacacs_key=bool(m.tacacs_key_enc),
        equipment_count=eq_count,
        created_at=m.created_at, updated_at=m.updated_at,
    )


@router.get("", response_model=list[ManufacturerOut], dependencies=[Depends(require_auditor)])
def list_manufacturers(db: Session = Depends(get_db)) -> list[ManufacturerOut]:
    counts = _counts(db)
    rows = db.execute(select(Manufacturer).order_by(Manufacturer.display_name)).scalars()
    return [_to_out(m, counts.get(m.id, 0)) for m in rows]


@router.get("/{manufacturer_id}/secret", response_model=ManufacturerSecretOut)
def reveal_manufacturer_secret(
    manufacturer_id: int, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_admin),
) -> ManufacturerSecretOut:
    m = db.get(Manufacturer, manufacturer_id)
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")
    audit.record(db, action="reveal_secret", entity_type="manufacturer", entity_id=m.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request))
    db.commit()
    return ManufacturerSecretOut(
        radius_secret=decrypt(m.radius_secret_enc) if m.radius_secret_enc else None
    )


@router.post("", response_model=ManufacturerOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(enforce_csrf)])
def create_manufacturer(
    body: ManufacturerCreate, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_admin),
) -> ManufacturerOut:
    if db.execute(select(Manufacturer).where(Manufacturer.name == body.name)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "já existe fabricante com esse identificador")
    m = Manufacturer(
        name=body.name, display_name=body.display_name, vendor_kind=body.vendor_kind,
        radius_vendor_id=body.radius_vendor_id, aaa_protocol=body.aaa_protocol, notes=body.notes,
        radius_secret_enc=encrypt(body.radius_secret) if body.radius_secret else None,
        tacacs_key_enc=encrypt(body.tacacs_key) if body.tacacs_key else None,
    )
    db.add(m)
    db.flush()
    audit.record(db, action="create", entity_type="manufacturer", entity_id=m.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 after={"name": m.name, "vendor_kind": m.vendor_kind.value,
                        "has_secret": bool(m.radius_secret_enc)})
    db.commit()
    return _to_out(m, 0)


@router.patch("/{manufacturer_id}", response_model=ManufacturerOut,
              dependencies=[Depends(enforce_csrf)])
def update_manufacturer(
    manufacturer_id: int, body: ManufacturerUpdate, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_admin),
) -> ManufacturerOut:
    m = db.get(Manufacturer, manufacturer_id)
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")

    before = {"vendor_kind": m.vendor_kind.value, "has_secret": bool(m.radius_secret_enc),
              "aaa_protocol": m.aaa_protocol.value}
    secret_changed = False
    tacacs_changed = False

    if body.display_name is not None:
        m.display_name = body.display_name
    if body.vendor_kind is not None:
        m.vendor_kind = body.vendor_kind
    if body.radius_vendor_id is not None:
        m.radius_vendor_id = body.radius_vendor_id
    if body.notes is not None:
        m.notes = body.notes
    if body.aaa_protocol is not None and body.aaa_protocol != m.aaa_protocol:
        m.aaa_protocol = body.aaa_protocol
        tacacs_changed = True
    if body.clear_secret:
        m.radius_secret_enc = None
        secret_changed = True
    elif body.radius_secret:
        m.radius_secret_enc = encrypt(body.radius_secret)
        secret_changed = True
    if body.clear_tacacs_key:
        m.tacacs_key_enc = None
        tacacs_changed = True
    elif body.tacacs_key:
        m.tacacs_key_enc = encrypt(body.tacacs_key)
        tacacs_changed = True
    db.flush()

    resynced = 0
    if secret_changed or tacacs_changed or body.vendor_kind is not None:
        resynced = radius_sync.resync_manufacturer_equipment(db, m)
    if tacacs_changed or body.vendor_kind is not None:
        tacacs_sync.regenerate(db)

    audit.record(db, action="update", entity_type="manufacturer", entity_id=m.id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 before=before,
                 after={"vendor_kind": m.vendor_kind.value, "has_secret": bool(m.radius_secret_enc),
                        "equipamentos_resincronizados": resynced})
    db.commit()
    counts = _counts(db)
    return _to_out(m, counts.get(m.id, 0))


@router.delete("/{manufacturer_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(enforce_csrf)])
def delete_manufacturer(
    manufacturer_id: int, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_admin),
) -> None:
    m = db.get(Manufacturer, manufacturer_id)
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "não encontrado")

    eq_count = db.execute(
        select(func.count()).select_from(Equipment).where(Equipment.manufacturer_id == m.id)
    ).scalar_one()
    if eq_count:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"fabricante em uso por {eq_count} equipamento(s)")
    attr_count = db.execute(
        select(func.count()).select_from(PrivilegeProfileAttr).where(
            PrivilegeProfileAttr.manufacturer_id == m.id
        )
    ).scalar_one()
    if attr_count:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"fabricante referenciado em {attr_count} atributo(s) de perfil")

    name = m.name
    db.delete(m)
    db.flush()
    tacacs_sync.regenerate(db)
    audit.record(db, action="delete", entity_type="manufacturer", entity_id=manufacturer_id,
                 actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
                 before={"name": name})
    db.commit()
