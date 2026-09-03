from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PrivilegeProfile(Base, TimestampMixin):
    __tablename__ = "app_privilege_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(default=False)

    attrs: Mapped[list["PrivilegeProfileAttr"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def group_name(self) -> str:
        return f"profile_{self.name}"


class PrivilegeProfileAttr(Base):
    __tablename__ = "app_privilege_profile_attr"
    __table_args__ = (
        UniqueConstraint("profile_id", "manufacturer_id", "attribute", name="uq_profile_attr"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("app_privilege_profile.id", ondelete="CASCADE")
    )
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("app_manufacturer.id"))
    attribute: Mapped[str] = mapped_column(String(64))   # ex.: Huawei-Exec-Privilege
    op: Mapped[str] = mapped_column(String(2), default=":=")
    value: Mapped[str] = mapped_column(String(253))       # ex.: 15

    profile: Mapped[PrivilegeProfile] = relationship(back_populates="attrs")
