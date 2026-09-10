from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LgpdSettings(Base, TimestampMixin):
    """Configuração de privacidade/LGPD: identificação do controlador exibida no
    Aviso de Privacidade e os prazos de retenção que disparam a exclusão
    automática de dados. Linha única — sempre lemos/atualizamos a primeira.
    """

    __tablename__ = "app_lgpd_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_name: Mapped[str] = mapped_column(String(190), default="")
    dpo_email: Mapped[str] = mapped_column(String(190), default="")
    # Prazos em dias; 0 => nunca apaga automaticamente.
    accounting_retention_days: Mapped[int] = mapped_column(Integer, default=0)
    audit_retention_days: Mapped[int] = mapped_column(Integer, default=0)
    auth_user_retention_days: Mapped[int] = mapped_column(Integer, default=0)
    # Marca do último passo de expurgo — usada como claim atômico entre os
    # workers do gunicorn (só um roda por janela de 24h).
    last_purge_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
