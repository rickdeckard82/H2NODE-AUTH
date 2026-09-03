"""fabricante: vendor_kind + segredo RADIUS padrão; equipamento com segredo opcional

Revision ID: 0002_manufacturer_secret
Revises: 0001_initial
Create Date: 2026-01-02
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_manufacturer_secret"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

VK = sa.Enum(
    "huawei", "juniper", "datacom", "mikrotik", "generic",
    name="vendorkind", native_enum=False, length=16,
)


def upgrade() -> None:
    op.add_column(
        "app_manufacturer",
        sa.Column("vendor_kind", VK, nullable=False, server_default="generic"),
    )
    op.add_column(
        "app_manufacturer",
        sa.Column("radius_secret_enc", sa.String(512), nullable=True),
    )
    op.alter_column(
        "app_manufacturer", "name",
        existing_type=sa.String(20), type_=sa.String(40), existing_nullable=False,
    )
    # backfill: fabricantes conhecidos herdam a família pelo próprio nome
    op.execute(
        "UPDATE app_manufacturer SET vendor_kind = name "
        "WHERE name IN ('huawei','juniper','datacom','mikrotik')"
    )

    # equipamento pode não ter segredo próprio (herda do fabricante)
    op.alter_column(
        "app_equipment", "radius_secret_enc",
        existing_type=sa.String(512), nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "app_equipment", "radius_secret_enc",
        existing_type=sa.String(512), nullable=False,
    )
    op.alter_column(
        "app_manufacturer", "name",
        existing_type=sa.String(40), type_=sa.String(20), existing_nullable=False,
    )
    op.drop_column("app_manufacturer", "radius_secret_enc")
    op.drop_column("app_manufacturer", "vendor_kind")
