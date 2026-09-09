"""Códigos de recuperação do 2FA (app_mfa_recovery_code)

Gerados em lote quando o utilizador ativa o 2FA; uso único; guardados só como
hash Argon2. Servem para entrar ou desativar o 2FA sem o dispositivo TOTP.

Revision ID: 0012_mfa_recovery
Revises: 0011_require_ma
Create Date: 2026-09-08
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_mfa_recovery"
down_revision = "0011_require_ma"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_mfa_recovery_code",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "system_user_id",
            sa.Integer,
            sa.ForeignKey("app_system_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("used_at", sa.DateTime, nullable=True),
    )
    op.create_index(
        "ix_app_mfa_recovery_code_system_user_id",
        "app_mfa_recovery_code",
        ["system_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_app_mfa_recovery_code_system_user_id", "app_mfa_recovery_code")
    op.drop_table("app_mfa_recovery_code")
