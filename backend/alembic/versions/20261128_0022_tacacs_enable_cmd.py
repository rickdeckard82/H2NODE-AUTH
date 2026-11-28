"""TACACS+: nível de enable e autorização de comandos por perfil

Revision ID: 0022_tacacs_enable_cmd
Revises: 0021_auth_user_reset
Create Date: 2026-11-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0022_tacacs_enable_cmd"
down_revision = "0021_auth_user_reset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_privilege_profile", sa.Column("tacacs_enable_level", sa.Integer, nullable=True)
    )
    op.add_column("app_privilege_profile", sa.Column("tacacs_cmd_allow", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("app_privilege_profile", "tacacs_cmd_allow")
    op.drop_column("app_privilege_profile", "tacacs_enable_level")
