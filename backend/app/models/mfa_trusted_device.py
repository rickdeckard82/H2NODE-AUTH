from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MfaTrustedDevice(Base):
    """Navegador em que o usuário marcou "lembrar deste dispositivo" ao passar
    pelo 2FA.

    Enquanto o cookie correspondente estiver presente e a linha não tiver
    expirado, o login pula a 2ª etapa. Guardado só como hash SHA-256 de um token
    aleatório de 256 bits — o token em claro vive apenas no cookie do navegador.
    As linhas são descartadas ao desativar o 2FA ou trocar a senha.
    """

    __tablename__ = "app_mfa_trusted_device"

    id: Mapped[int] = mapped_column(primary_key=True)
    system_user_id: Mapped[int] = mapped_column(
        ForeignKey("app_system_user.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)

    user: Mapped["SystemUser"] = relationship(back_populates="mfa_trusted_devices")  # noqa: F821
