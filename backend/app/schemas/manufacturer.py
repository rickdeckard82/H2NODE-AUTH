from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.manufacturer import AaaProtocol, VendorKind


class ManufacturerBase(BaseModel):
    display_name: str = Field(min_length=1, max_length=64)
    vendor_kind: VendorKind = VendorKind.generic
    radius_vendor_id: int | None = Field(default=None, ge=1)
    aaa_protocol: AaaProtocol = AaaProtocol.radius
    notes: str | None = Field(default=None, max_length=255)


class ManufacturerCreate(ManufacturerBase):
    name: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    # Segredo RADIUS / chave TACACS+ padrão do fabricante (opcionais).
    radius_secret: str | None = Field(default=None, min_length=6, max_length=128)
    tacacs_key: str | None = Field(default=None, min_length=6, max_length=128)


class ManufacturerUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    vendor_kind: VendorKind | None = None
    radius_vendor_id: int | None = Field(default=None, ge=1)
    aaa_protocol: AaaProtocol | None = None
    notes: str | None = Field(default=None, max_length=255)
    radius_secret: str | None = Field(default=None, min_length=6, max_length=128)
    clear_secret: bool = False
    tacacs_key: str | None = Field(default=None, min_length=6, max_length=128)
    clear_tacacs_key: bool = False


class ManufacturerOut(ManufacturerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    has_secret: bool
    has_tacacs_key: bool = False
    equipment_count: int = 0
    created_at: datetime
    updated_at: datetime


class ManufacturerSecretOut(BaseModel):
    radius_secret: str | None
