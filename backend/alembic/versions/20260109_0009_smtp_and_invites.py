"""SMTP settings + convite de registo para utilizadores do painel

Revision ID: 0009_smtp_invites
Revises: 0008_tacacs
Create Date: 2026-01-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_smtp_invites"
down_revision = "0008_tacacs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "app_system_user", "password_hash",
        existing_type=sa.String(255), nullable=True,
    )

    op.create_table(
        "app_smtp_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer, nullable=False, server_default="587"),
        sa.Column("username", sa.String(255)),
        sa.Column("password_enc", sa.String(512)),
        sa.Column("use_tls", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("use_ssl", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("from_email", sa.String(190), nullable=False),
        sa.Column("from_name", sa.String(190)),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "app_user_invite",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "system_user_id", sa.Integer,
            sa.ForeignKey("app_system_user.id", ondelete="CASCADE"), nullable=False, index=True,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("used_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("app_user_invite")
    op.drop_table("app_smtp_settings")
    op.alter_column(
        "app_system_user", "password_hash",
        existing_type=sa.String(255), nullable=False,
    )
