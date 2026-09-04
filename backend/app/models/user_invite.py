from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UserInvite(Base, TimestampMixin):
    """Convite para o utilizador do painel terminar o registo criando a própria
    senha. Guardamos só o hash SHA-256 do token — o valor em claro só existe no
    link enviado por e-mail."""

    __tablename__ = "app_user_invite"

    id: Mapped[int] = mapped_column(primary_key=True)
    system_user_id: Mapped[int] = mapped_column(
        ForeignKey("app_system_user.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
