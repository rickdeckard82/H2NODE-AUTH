"""Bloqueio de login crescente (lockout_strikes) + 2FA (mfa_enabled)

Revision ID: 0010_lockout_mfa
Revises: 0009_smtp_invites
Create Date: 2026-01-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_lockout_mfa"
down_revision = "0009_smtp_invites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_system_user",
        sa.Column("lockout_strikes", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "app_system_user",
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("app_system_user", "mfa_enabled")
    op.drop_column("app_system_user", "lockout_strikes")
