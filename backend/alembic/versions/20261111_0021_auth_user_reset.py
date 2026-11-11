"""Token de redefinição de senha de usuários de autenticação

Revision ID: 0021_auth_user_reset
Revises: 0020_site
Create Date: 2026-11-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0021_auth_user_reset"
down_revision = "0020_site"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_auth_user_reset",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "auth_user_id",
            sa.Integer,
            sa.ForeignKey("app_auth_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("used_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_app_auth_user_reset_auth_user_id", "app_auth_user_reset", ["auth_user_id"])
    op.create_index(
        "ix_app_auth_user_reset_token_hash", "app_auth_user_reset", ["token_hash"], unique=True
    )


def downgrade() -> None:
    op.drop_table("app_auth_user_reset")
