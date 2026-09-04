"""Mantém as tabelas do FreeRADIUS em sincronia com o modelo da aplicação.

Todas as funções operam na Session recebida (mesma transação do caller), de modo
que a escrita em `app_*` e o reflexo em `rad*`/`nas` são atômicos.
"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt
from app.models import (
    AuthUser,
    Equipment,
    Manufacturer,
    Nas,
    PrivilegeProfile,
    RadCheck,
    RadGroupReply,
    RadReply,
    RadUserGroup,
    VendorKind,
)
from app.models.manufacturer import AaaProtocol
from app.services.password import (
    RADIUS_NT_PASSWORD_ATTR,
    RADIUS_PASSWORD_ATTR,
    make_nt_hash,
    make_ssha512,
)

# ─────────────────────────── usuários de auth ───────────────────────────


def sync_auth_user(db: Session, user: AuthUser, *, password: str | None = None) -> None:
    profile = db.get(PrivilegeProfile, user.privilege_profile_id)
    if profile is None:
        raise ValueError("perfil de privilégio inexistente")

    # radcheck: senha (só reescreve se veio senha nova). Dois verificadores:
    # SSHA2-512 p/ PAP (Huawei/Juniper/Datacom) e NT-Password p/ MS-CHAPv2
    # (login administrativo do MikroTik). Nenhum é texto claro.
    if password is not None:
        db.execute(
            delete(RadCheck).where(
                RadCheck.username == user.username,
                RadCheck.attribute.in_(
                    [
                        RADIUS_PASSWORD_ATTR,
                        RADIUS_NT_PASSWORD_ATTR,
                        "Cleartext-Password",
                        "Crypt-Password",
                    ]
                ),
            )
        )
        db.add(
            RadCheck(
                username=user.username,
                attribute=RADIUS_PASSWORD_ATTR,
                op=":=",
                value=make_ssha512(password),
            )
        )
        db.add(
            RadCheck(
                username=user.username,
                attribute=RADIUS_NT_PASSWORD_ATTR,
                op=":=",
                value=make_nt_hash(password),
            )
        )

    # radusergroup: exatamente um grupo, o do perfil
    db.execute(delete(RadUserGroup).where(RadUserGroup.username == user.username))
    db.add(
        RadUserGroup(username=user.username, groupname=profile.group_name, priority=1)
    )


def rename_auth_user(db: Session, old_username: str, new_username: str) -> None:
    if old_username == new_username:
        return
    for model in (RadCheck, RadReply, RadUserGroup):
        for row in db.execute(
            select(model).where(model.username == old_username)
        ).scalars():
            row.username = new_username


def delete_auth_user(db: Session, username: str) -> None:
    for model in (RadCheck, RadReply, RadUserGroup):
        db.execute(delete(model).where(model.username == username))


# ─────────────────────────── perfis / grupos ───────────────────────────


def sync_profile_groupreply(db: Session, profile: PrivilegeProfile) -> None:
    db.execute(
        delete(RadGroupReply).where(RadGroupReply.groupname == profile.group_name)
    )
    for attr in profile.attrs:
        db.add(
            RadGroupReply(
                groupname=profile.group_name,
                attribute=attr.attribute,
                op=attr.op or ":=",
                value=attr.value,
            )
        )


def rename_profile_group(db: Session, old_name: str, new_name: str) -> None:
    if old_name == new_name:
        return
    old_group, new_group = f"profile_{old_name}", f"profile_{new_name}"
    for row in db.execute(
        select(RadGroupReply).where(RadGroupReply.groupname == old_group)
    ).scalars():
        row.groupname = new_group
    for row in db.execute(
        select(RadUserGroup).where(RadUserGroup.groupname == old_group)
    ).scalars():
        row.groupname = new_group


def delete_profile_group(db: Session, group_name: str) -> None:
    db.execute(delete(RadGroupReply).where(RadGroupReply.groupname == group_name))


# ────────────────────────────── equipamentos ─────────────────────────────


def _nas_by_name(db: Session, nasname: str) -> Nas | None:
    return db.execute(select(Nas).where(Nas.nasname == nasname)).scalar_one_or_none()


def resolve_secret(eq: Equipment, manufacturer: Manufacturer) -> str:
    """Segredo efetivo do equipamento: o próprio, senão o padrão do fabricante."""
    if eq.radius_secret_enc:
        return decrypt(eq.radius_secret_enc)
    if manufacturer.radius_secret_enc:
        return decrypt(manufacturer.radius_secret_enc)
    raise ValueError(
        "Sem segredo RADIUS: informe um no equipamento ou cadastre o segredo "
        f"padrão no fabricante '{manufacturer.name}'."
    )


def sync_equipment(db: Session, eq: Equipment, *, manufacturer: Manufacturer) -> None:
    # Equipamento TACACS+ não é cliente RADIUS: garante que não fique em `nas`.
    if (eq.aaa_protocol or manufacturer.aaa_protocol) == AaaProtocol.tacacs:
        db.execute(delete(Nas).where(Nas.nasname == eq.mgmt_ip))
        return

    secret = resolve_secret(eq, manufacturer)
    nas = _nas_by_name(db, eq.mgmt_ip)
    if nas is None:
        nas = Nas(nasname=eq.mgmt_ip)
        db.add(nas)
    nas.shortname = eq.shortname
    nas.secret = secret
    nas.type = (
        manufacturer.vendor_kind.value
        if manufacturer.vendor_kind != VendorKind.generic
        else "other"
    )
    nas.description = f"{eq.name} ({eq.model or manufacturer.display_name})"[:200]


def resync_manufacturer_equipment(db: Session, manufacturer: Manufacturer) -> int:
    """Re-sincroniza os equipamentos do grupo (segredo/protocolo herdados podem
    ter mudado — inclui mover entre `nas` e TACACS+)."""
    count = 0
    rows = db.execute(
        select(Equipment).where(Equipment.manufacturer_id == manufacturer.id)
    ).scalars()
    for eq in rows:
        sync_equipment(db, eq, manufacturer=manufacturer)
        count += 1
    return count


def rename_equipment_nas(db: Session, old_ip: str, new_ip: str) -> None:
    if old_ip == new_ip:
        return
    nas = _nas_by_name(db, old_ip)
    if nas is not None:
        nas.nasname = new_ip


def delete_equipment_nas(db: Session, mgmt_ip: str) -> None:
    db.execute(delete(Nas).where(Nas.nasname == mgmt_ip))
