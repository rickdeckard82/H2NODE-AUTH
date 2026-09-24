"""radpostauth: IP real de origem do técnico (callingstationid)

A tela Authentication mostrava em "Origem" o IP do equipamento
(`nasipaddress`) e em "Destino" o IP deste próprio servidor AAA
(`serveripaddress`) — nenhum dos dois é o IP de onde o técnico realmente
conecta. Acrescenta `callingstationid` (mesmo conceito já usado em
`cmd_acct`/`radacct`) para guardar esse IP real de origem:

- RADIUS: `Calling-Station-Id` (site `default`, bloco `post-auth`).
- TACACS+: campo `rem-addr` do access.log do tac_plus-ng
  (`tacacs/authlog_import.py`).

O backend passa a usar `callingstationid` como "Origem" (IP do técnico) e
`nasipaddress` como "Destino" (equipamento acessado).

Revision ID: 0017_radpostauth_callingstationid
Revises: 0016_system_user_language
Create Date: 2026-09-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0017_radpostauth_callingstationid"
down_revision = "0016_system_user_language"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("radpostauth", sa.Column("callingstationid", sa.String(45), nullable=True))


def downgrade() -> None:
    op.drop_column("radpostauth", "callingstationid")
