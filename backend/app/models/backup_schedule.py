from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BackupSchedule(Base, TimestampMixin):
    """Backup automático por FTP/FTPS (linha única). Executado pelo container
    `backup-worker`; a API só grava a configuração e pede execuções imediatas."""

    __tablename__ = "app_backup_schedule"

    id: Mapped[int] = mapped_column(primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # Horário diário "HH:MM" no fuso `timezone`.
    run_time: Mapped[str] = mapped_column(String(5), default="02:30")
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo")
    include_accounting: Mapped[bool] = mapped_column(Boolean, default=True)
    # Cifra com a FERNET_KEY (.sql.enc); desligado gera .sql.gz em claro.
    encrypted: Mapped[bool] = mapped_column(Boolean, default=True)
    keep_count: Mapped[int] = mapped_column(Integer, default=7)
    ftp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ftp_port: Mapped[int] = mapped_column(Integer, default=21)
    ftp_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Fernet. Nunca devolvida pela API; em branco no formulário mantém a atual.
    ftp_password_enc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ftp_directory: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ftp_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    # Destino só de gravação (ex.: Pulse Backup): envia direto com o nome final e
    # não apaga cópias antigas (a retenção fica a cargo do servidor de backup).
    ftp_write_only: Mapped[bool] = mapped_column(Boolean, default=False)
    run_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_message: Mapped[str | None] = mapped_column(Text, nullable=True)
