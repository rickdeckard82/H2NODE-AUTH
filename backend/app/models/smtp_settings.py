from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SmtpSettings(Base, TimestampMixin):
    """Configuração do servidor SMTP usado para e-mails do painel (convites de
    registro etc). Linha única — sempre lemos/atualizamos a primeira encontrada."""

    __tablename__ = "app_smtp_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer, default=587)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Fernet. NULL => servidor não exige autenticação.
    password_enc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    use_tls: Mapped[bool] = mapped_column(Boolean, default=True)  # STARTTLS
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=False)  # SMTPS implícito (porta 465)
    from_email: Mapped[str] = mapped_column(String(190))
    from_name: Mapped[str | None] = mapped_column(String(190), nullable=True)
