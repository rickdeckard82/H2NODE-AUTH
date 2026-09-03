"""bloqueio de conta do painel após tentativas de login malsucedidas

Revision ID: 0003_login_lockout
Revises: 0002_manufacturer_secret
Create Date: 2026-01-03
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_login_lockout"
down_revision = "0002_manufacturer_secret"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_system_user",
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "app_system_user",
        sa.Column("locked_until", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("app_system_user", "locked_until")
    op.drop_column("app_system_user", "failed_login_count")
