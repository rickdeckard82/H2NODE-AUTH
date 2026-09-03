from sqlalchemy import ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AuthUserGroup(Base, TimestampMixin):
    """Grupo de usuários de autenticação com allowlist de IP de origem.

    Se um usuário pertence a um grupo e o IP de origem do request RADIUS não
    casa com nenhuma das faixas do grupo, o FreeRADIUS rejeita (Access-Reject).
    """

    __tablename__ = "app_auth_user_group"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    cidrs: Mapped[list["AuthGroupCidr"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AuthGroupCidr(Base):
    """Uma faixa (IP ou CIDR) permitida como origem para um grupo.

    ip_start/ip_end guardam os limites em forma binária compatível com
    INET6_ATON() do MySQL (4 bytes p/ IPv4, 16 p/ IPv6). `family` = 4 ou 6.
    """

    __tablename__ = "app_auth_group_cidr"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("app_auth_user_group.id", ondelete="CASCADE"), index=True
    )
    cidr: Mapped[str] = mapped_column(String(64))       # exibição: "10.0.0.0/24"
    family: Mapped[int] = mapped_column(Integer)        # 4 ou 6
    ip_start: Mapped[bytes] = mapped_column(LargeBinary(16))
    ip_end: Mapped[bytes] = mapped_column(LargeBinary(16))
    note: Mapped[str | None] = mapped_column(String(120), nullable=True)

    group: Mapped[AuthUserGroup] = relationship(back_populates="cidrs")
