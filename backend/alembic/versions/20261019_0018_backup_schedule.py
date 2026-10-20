"""Backup automático agendado por FTP (app_backup_schedule)

Linha única com o horário diário, o destino FTP/FTPS (senha cifrada com a
FERNET_KEY), a retenção no destino e o resultado da última execução. Quem
executa é o container `backup-worker`.

Revision ID: 0018_backup_schedule
Revises: 0017_radpostauth_callerip
Create Date: 2026-10-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0018_backup_schedule"
down_revision = "0017_radpostauth_callerip"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_backup_schedule",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("run_time", sa.String(5), nullable=False, server_default="02:30"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/Sao_Paulo"),
        sa.Column("include_accounting", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("encrypted", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("keep_count", sa.Integer, nullable=False, server_default="7"),
        sa.Column("ftp_host", sa.String(255), nullable=True),
        sa.Column("ftp_port", sa.Integer, nullable=False, server_default="21"),
        sa.Column("ftp_user", sa.String(255), nullable=True),
        sa.Column("ftp_password_enc", sa.String(512), nullable=True),
        sa.Column("ftp_directory", sa.String(500), nullable=True),
        sa.Column("ftp_tls", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("ftp_write_only", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("run_requested_at", sa.DateTime, nullable=True),
        sa.Column("last_attempt_at", sa.DateTime, nullable=True),
        sa.Column("last_success_at", sa.DateTime, nullable=True),
        sa.Column("last_status", sa.String(20), nullable=True),
        sa.Column("last_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("app_backup_schedule")
