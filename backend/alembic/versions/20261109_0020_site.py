"""Cadastro de Site/Localização (app_site)

Popula a tabela com os valores de site já usados em app_equipment.

Revision ID: 0020_site
Revises: 0019_radius_svc_privprofile
Create Date: 2026-11-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0020_site"
down_revision = "0019_radius_svc_privprofile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_site",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_app_site_name", "app_site", ["name"], unique=True)
    op.execute(
        "INSERT INTO app_site (name) SELECT DISTINCT site FROM app_equipment "
        "WHERE site IS NOT NULL AND site <> ''"
    )


def downgrade() -> None:
    op.drop_index("ix_app_site_name", table_name="app_site")
    op.drop_table("app_site")
