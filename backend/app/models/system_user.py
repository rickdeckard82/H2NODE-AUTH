import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SystemRole(str, enum.Enum):
    superadmin = "superadmin"  # tudo, inclusive gerir utilizadores do painel
    admin = "admin"            # gere usuários de auth, equipamentos e perfis
    operator = "operator"      # cadastra usuários de auth; leitura de equipamentos
    auditor = "auditor"        # somente leitura (inclui accounting e auditoria)


class SystemUser(Base, TimestampMixin):
    __tablename__ = "app_system_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(190), unique=True)
    full_name: Mapped[str] = mapped_column(String(190))
    # NULL => convite de registo pendente (usuário ainda não criou a senha).
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[SystemRole] = mapped_column(
        Enum(SystemRole, native_enum=False, length=20), default=SystemRole.operator
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Fuso IANA para exibir datas no painel (conversão só na apresentação).
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo")
    mfa_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None
