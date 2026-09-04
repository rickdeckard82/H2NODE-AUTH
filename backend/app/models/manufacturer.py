import enum

from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class VendorKind(str, enum.Enum):
    """Família do fabricante — define como o FreeRADIUS traduz o perfil em VSA."""

    huawei = "huawei"
    juniper = "juniper"
    datacom = "datacom"
    mikrotik = "mikrotik"
    generic = "generic"  # não filtra VSA (equipamento ignora atributos alheios)


class AaaProtocol(str, enum.Enum):
    """Protocolo AAA do equipamento. MikroTik só fala RADIUS."""

    radius = "radius"
    tacacs = "tacacs"


class Manufacturer(Base, TimestampMixin):
    __tablename__ = "app_manufacturer"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True, index=True)  # slug
    display_name: Mapped[str] = mapped_column(String(64))
    vendor_kind: Mapped[VendorKind] = mapped_column(
        Enum(VendorKind, native_enum=False, length=16), default=VendorKind.generic
    )
    radius_vendor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Segredo RADIUS padrão do fabricante (Fernet). Equipamentos sem segredo
    # próprio herdam este valor.
    radius_secret_enc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Protocolo AAA padrão do grupo; equipamentos herdam se não definirem o seu.
    aaa_protocol: Mapped[AaaProtocol] = mapped_column(
        Enum(AaaProtocol, native_enum=False, length=16), default=AaaProtocol.radius
    )
    # Chave TACACS+ padrão do grupo (Fernet). Herdável, como o radius_secret.
    tacacs_key_enc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
