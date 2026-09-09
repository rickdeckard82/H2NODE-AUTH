"""Seed idempotente: fabricantes, perfis de privilégio e primeiro admin.

Executado no start do container (ver Dockerfile) e via `make seed`.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.logging import logger
from app.core.security import hash_password
from app.models import (
    Manufacturer,
    PrivilegeProfile,
    PrivilegeProfileAttr,
    SystemRole,
    SystemUser,
    VendorKind,
)
from app.services import radius_sync

# Fabricantes comuns pré-cadastrados como ponto de partida (editáveis/removíveis
# na página "Fabricantes"). Sem segredo — o operador cadastra o segredo padrão lá.
MANUFACTURERS = [
    ("huawei", "Huawei", VendorKind.huawei, 2011),
    ("juniper", "Juniper", VendorKind.juniper, 2636),
    ("datacom", "Datacom", VendorKind.datacom, 3709),
    ("mikrotik", "Mikrotik", VendorKind.mikrotik, 14988),
    ("a10", "A10 Networks", VendorKind.a10, 22610),
]

# perfil -> descrição, {vendor_kind (slug) -> (attribute, value)}
PROFILES: dict[str, tuple[str, dict[str, tuple[str, str]]]] = {
    "admin-full": (
        "Acesso administrativo total (nível máximo em cada fabricante)",
        {
            "huawei": ("Huawei-Exec-Privilege", "15"),
            "juniper": ("Juniper-Local-User-Name", "super-user"),
            "datacom": ("Datacom-Privilege-Level", "15"),
            "mikrotik": ("Mikrotik-Group", "full"),
            "a10": ("A10-Admin-Privilege", "3"),
        },
    ),
    "operator": (
        "Operação: pode configurar, sem administração do dispositivo",
        {
            "huawei": ("Huawei-Exec-Privilege", "10"),
            "juniper": ("Juniper-Local-User-Name", "operator"),
            "datacom": ("Datacom-Privilege-Level", "10"),
            "mikrotik": ("Mikrotik-Group", "write"),
            "a10": ("A10-Admin-Privilege", "12"),
        },
    ),
    "read-only": (
        "Somente leitura / auditoria",
        {
            "huawei": ("Huawei-Exec-Privilege", "1"),
            "juniper": ("Juniper-Local-User-Name", "read-only"),
            "datacom": ("Datacom-Privilege-Level", "1"),
            "mikrotik": ("Mikrotik-Group", "read"),
            "a10": ("A10-Admin-Privilege", "14"),
        },
    ),
}

# priv-lvl TACACS+ (exec) equivalente de cada perfil interno.
PROFILE_TACACS_LEVEL = {"admin-full": 15, "operator": 10, "read-only": 1}


def seed_manufacturers(db: Session) -> dict[str, Manufacturer]:
    existing = {m.name: m for m in db.execute(select(Manufacturer)).scalars()}
    for name, display, kind, vendor_id in MANUFACTURERS:
        if name not in existing:
            m = Manufacturer(
                name=name, display_name=display, vendor_kind=kind, radius_vendor_id=vendor_id
            )
            db.add(m)
            existing[name] = m
    db.flush()
    return existing


def seed_profiles(db: Session, mfrs: dict[str, Manufacturer]) -> None:
    for pname, (desc, vendor_map) in PROFILES.items():
        profile = db.execute(
            select(PrivilegeProfile).where(PrivilegeProfile.name == pname)
        ).scalar_one_or_none()
        if profile is None:
            profile = PrivilegeProfile(
                name=pname, description=desc, is_builtin=True,
                tacacs_priv_level=PROFILE_TACACS_LEVEL.get(pname, 1),
            )
            db.add(profile)
            db.flush()
        if not profile.attrs:
            for mname, (attr, value) in vendor_map.items():
                m = mfrs.get(mname)
                if m is None:  # fabricante removido pelo operador — pula
                    continue
                db.add(
                    PrivilegeProfileAttr(
                        profile_id=profile.id, manufacturer_id=m.id,
                        attribute=attr, op=":=", value=value,
                    )
                )
            db.flush()
            db.refresh(profile)
            radius_sync.sync_profile_groupreply(db, profile)


def seed_admin(db: Session) -> None:
    if db.execute(select(SystemUser).limit(1)).first():
        return
    if not settings.bootstrap_admin_password:
        logger.warning("seed_admin_skipped", reason="BOOTSTRAP_ADMIN_PASSWORD vazio")
        return
    db.add(
        SystemUser(
            username=settings.bootstrap_admin_username,
            email=settings.bootstrap_admin_email,
            full_name="Administrador",
            role=SystemRole.superadmin,
            is_active=True,
            password_hash=hash_password(settings.bootstrap_admin_password),
        )
    )
    logger.info("seed_admin_created", username=settings.bootstrap_admin_username)


def main() -> None:
    db = SessionLocal()
    try:
        mfrs = seed_manufacturers(db)
        seed_profiles(db, mfrs)
        seed_admin(db)
        db.commit()
        logger.info("seed_done")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
