"""Idioma do usuário do painel (app_system_user.language)

pt-BR (padrão) ou en-US. Definido no cadastro do usuário e alterável pelo
próprio no menu do painel.

Revision ID: 0016_system_user_language
Revises: 0015_lgpd_settings
Create Date: 2026-09-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0016_system_user_language"
down_revision = "0015_lgpd_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_system_user",
        sa.Column("language", sa.String(8), nullable=False, server_default="pt-BR"),
    )


def downgrade() -> None:
    op.drop_column("app_system_user", "language")
