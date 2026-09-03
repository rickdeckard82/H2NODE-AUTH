"""fuso horário de exibição por utilizador do sistema

Revision ID: 0006_system_user_timezone
Revises: 0005_auth_user_groups
Create Date: 2026-01-06
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_system_user_timezone"
down_revision = "0005_auth_user_groups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_system_user",
        sa.Column(
            "timezone", sa.String(64), nullable=False,
            server_default="America/Sao_Paulo",
        ),
    )


def downgrade() -> None:
    op.drop_column("app_system_user", "timezone")
