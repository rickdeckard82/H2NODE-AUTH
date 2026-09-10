"""Configuração LGPD (app_lgpd_settings)

Identificação do controlador exibida no Aviso de Privacidade + prazos de
retenção que disparam a exclusão automática de dados (accounting/logins,
auditoria e usuários de autenticação inativos).

Revision ID: 0015_lgpd_settings
Revises: 0014_mfa_trusted_device
Create Date: 2026-09-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0015_lgpd_settings"
down_revision = "0014_mfa_trusted_device"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_lgpd_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_name", sa.String(190), nullable=False, server_default=""),
        sa.Column("dpo_email", sa.String(190), nullable=False, server_default=""),
        sa.Column("accounting_retention_days", sa.Integer, nullable=False, server_default="0"),
        sa.Column("audit_retention_days", sa.Integer, nullable=False, server_default="0"),
        sa.Column("auth_user_retention_days", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_purge_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("app_lgpd_settings")
