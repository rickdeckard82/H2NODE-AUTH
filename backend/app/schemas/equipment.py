from datetime import datetime
from ipaddress import ip_address

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.equipment import EquipmentStatus
from app.models.manufacturer import AaaProtocol, VendorKind


class EquipmentBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    mgmt_ip: str = Field(max_length=45)
    manufacturer_id: int
    model: str | None = Field(default=None, max_length=120)
    site: str | None = Field(default=None, max_length=120)
    shortname: str = Field(min_length=1, max_length=32, pattern=r"^[a-zA-Z0-9._-]+$")
    coa_port: int = Field(default=3799, ge=1, le=65535)
    status: EquipmentStatus = EquipmentStatus.active
    # None => herda o protocolo do grupo (fabricante).
    aaa_protocol: AaaProtocol | None = None
    description: str | None = Field(default=None, max_length=255)

    @field_validator("mgmt_ip")
    @classmethod
    def _valid_ip(cls, v: str) -> str:
        ip_address(v)  # levanta ValueError se inválido
        return v


class EquipmentCreate(EquipmentBase):
    # Opcional: em branco => herda o segredo/chave padrão do fabricante.
    radius_secret: str | None = Field(default=None, min_length=6, max_length=128)
    tacacs_key: str | None = Field(default=None, min_length=6, max_length=128)


class EquipmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    mgmt_ip: str | None = Field(default=None, max_length=45)
    manufacturer_id: int | None = None
    model: str | None = Field(default=None, max_length=120)
    site: str | None = Field(default=None, max_length=120)
    shortname: str | None = Field(default=None, min_length=1, max_length=32, pattern=r"^[a-zA-Z0-9._-]+$")
    coa_port: int | None = Field(default=None, ge=1, le=65535)
    status: EquipmentStatus | None = None
    description: str | None = Field(default=None, max_length=255)
    radius_secret: str | None = Field(default=None, min_length=6, max_length=128)
    # true => volta a herdar o segredo do fabricante
    inherit_secret: bool = False
    # None => não mexe; "radius"/"tacacs" fixa; use inherit_protocol p/ voltar a herdar
    aaa_protocol: AaaProtocol | None = None
    inherit_protocol: bool = False
    tacacs_key: str | None = Field(default=None, min_length=6, max_length=128)
    inherit_tacacs_key: bool = False

    @field_validator("mgmt_ip")
    @classmethod
    def _valid_ip(cls, v: str | None) -> str | None:
        if v is not None:
            ip_address(v)
        return v


class EquipmentOut(EquipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    manufacturer_name: str
    manufacturer_display: str
    vendor_kind: VendorKind
    has_own_secret: bool
    secret_source: str  # "equipment" | "manufacturer" | "none"
    # protocolo efetivo (já resolvida a herança) e de onde vem cada coisa
    effective_protocol: AaaProtocol
    protocol_source: str  # "equipment" | "manufacturer"
    has_own_tacacs_key: bool = False
    tacacs_key_source: str = "none"  # "equipment" | "manufacturer" | "none"
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EquipmentSecretOut(BaseModel):
    radius_secret: str | None
    source: str  # "equipment" | "manufacturer" | "none"
