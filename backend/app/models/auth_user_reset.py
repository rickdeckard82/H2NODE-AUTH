from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AuthUserReset(Base, TimestampMixin):
    """Link de redefinição de senha enviado por e-mail a um usuário de
    autenticação (RADIUS). Guarda só o hash SHA-256 do token."""

    __tablename__ = "app_auth_user_reset"

    id: Mapped[int] = mapped_column(primary_key=True)
    auth_user_id: Mapped[int] = mapped_column(
        ForeignKey("app_auth_user.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
