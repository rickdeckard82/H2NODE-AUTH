"""radpostauth: IP de origem/destino + protocolo (RADIUS/TACACS+)

Acrescenta colunas próprias do H2NODE Auth à tabela padrão `radpostauth`:

- `nasipaddress`    — IP de origem da tentativa (o equipamento).
- `serveripaddress` — IP de destino (o servidor AAA que recebeu o pacote).
- `protocol`        — `radius` (gravado pelo site `default` do FreeRADIUS) ou
                      `tacacs` (importado do access.log do tac_plus-ng pelo
                      `tacacs/authlog_import.py`).

Fora do autogenerate (env.py: RADIUS_TABLES). Como em 0011 (`nas`), nada impede
acrescentar colunas próprias a uma tabela do schema FreeRADIUS; o `db/init` cria
só o schema padrão e as migrações somam as colunas do H2NODE Auth.

Revision ID: 0013_radpostauth_src_dst
Revises: 0012_mfa_recovery
Create Date: 2026-09-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0013_radpostauth_src_dst"
down_revision = "0012_mfa_recovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("radpostauth", sa.Column("nasipaddress", sa.String(45), nullable=True))
    op.add_column("radpostauth", sa.Column("serveripaddress", sa.String(45), nullable=True))
    op.add_column(
        "radpostauth",
        sa.Column("protocol", sa.String(8), nullable=False, server_default="radius"),
    )


def downgrade() -> None:
    op.drop_column("radpostauth", "protocol")
    op.drop_column("radpostauth", "serveripaddress")
    op.drop_column("radpostauth", "nasipaddress")
