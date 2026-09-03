import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.manufacturer import Manufacturer


class EquipmentStatus(str, enum.Enum):
    active = "active"
    maintenance = "maintenance"
    disabled = "disabled"


class Equipment(Base, TimestampMixin):
    __tablename__ = "app_equipment"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    mgmt_ip: Mapped[str] = mapped_column(String(45), unique=True, index=True)
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("app_manufacturer.id"))
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    site: Mapped[str | None] = mapped_column(String(120), nullable=True)
    shortname: Mapped[str] = mapped_column(String(32))
    # Fernet. NULL => herda o segredo do fabricante.
    radius_secret_enc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    coa_port: Mapped[int] = mapped_column(Integer, default=3799)
    status: Mapped[EquipmentStatus] = mapped_column(
        Enum(EquipmentStatus, native_enum=False, length=16), default=EquipmentStatus.active
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("app_system_user.id", ondelete="SET NULL"), nullable=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    manufacturer: Mapped[Manufacturer] = relationship(lazy="joined")
