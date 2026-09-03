from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.auth_group import AuthUserGroup
from app.models.base import Base, TimestampMixin
from app.models.privilege_profile import PrivilegeProfile


class AuthUser(Base, TimestampMixin):
    """Metadados do usuário que autentica nos equipamentos.

    A verdade para o FreeRADIUS vive em radcheck/radusergroup; esta tabela
    guarda o que o painel precisa e é mantida em sincronia pelo radius_sync.
    """

    __tablename__ = "app_auth_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(190), nullable=True)
    email: Mapped[str | None] = mapped_column(String(190), nullable=True)
    privilege_profile_id: Mapped[int] = mapped_column(ForeignKey("app_privilege_profile.id"))
    auth_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("app_auth_user_group.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_auth_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("app_system_user.id", ondelete="SET NULL"), nullable=True
    )

    profile: Mapped[PrivilegeProfile] = relationship(lazy="joined")
    auth_group: Mapped[AuthUserGroup | None] = relationship(lazy="joined")
