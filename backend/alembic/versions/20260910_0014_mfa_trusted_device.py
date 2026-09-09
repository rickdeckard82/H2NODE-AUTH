"""Dispositivos confiáveis do 2FA (app_mfa_trusted_device)

"Lembrar deste dispositivo": enquanto o cookie pr_td estiver presente e a linha
não tiver expirado, o login pula a 2ª etapa. Guardado só como hash SHA-256 de um
token aleatório de 256 bits.

Revision ID: 0014_mfa_trusted_device
Revises: 0013_radpostauth_src_dst
Create Date: 2026-09-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0014_mfa_trusted_device"
down_revision = "0013_radpostauth_src_dst"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_mfa_trusted_device",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "system_user_id",
            sa.Integer,
            sa.ForeignKey("app_system_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
    )
    op.create_index(
        "ix_app_mfa_trusted_device_system_user_id",
        "app_mfa_trusted_device",
        ["system_user_id"],
    )
    op.create_index(
        "ix_app_mfa_trusted_device_token_hash",
        "app_mfa_trusted_device",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_app_mfa_trusted_device_token_hash", "app_mfa_trusted_device")
    op.drop_index("ix_app_mfa_trusted_device_system_user_id", "app_mfa_trusted_device")
    op.drop_table("app_mfa_trusted_device")
