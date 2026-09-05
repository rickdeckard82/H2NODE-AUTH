"""Exceção por equipamento à exigência de Message-Authenticator (BlastRADIUS)

Para NAS com firmware antigo que não envia Message-Authenticator (ex.: RouterOS
pré-patch do CVE-2024-3596) — permite desligar a exigência só para esse
equipamento, sem afetar a política global (RADIUS_REQUIRE_MA).

Revision ID: 0011_require_ma
Revises: 0010_lockout_mfa
Create Date: 2026-09-06
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_require_ma"
down_revision = "0010_lockout_mfa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_equipment",
        sa.Column(
            "radius_require_message_authenticator",
            sa.Boolean, nullable=False, server_default=sa.true(),
        ),
    )
    # `nas` é do schema padrão do FreeRADIUS (db/init/00_radius_schema.sql), mas
    # nada impede acrescentar uma coluna própria — o app_equipment é quem manda,
    # radius_sync.py propaga o valor para cá a cada sync.
    op.add_column(
        "nas",
        sa.Column(
            "require_message_authenticator",
            sa.Boolean, nullable=False, server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("nas", "require_message_authenticator")
    op.drop_column("app_equipment", "radius_require_message_authenticator")
