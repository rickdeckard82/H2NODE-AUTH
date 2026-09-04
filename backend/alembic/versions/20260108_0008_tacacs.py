"""TACACS+: protocolo por equipamento/grupo, chave TACACS+, nível de privilégio

Revision ID: 0008_tacacs
Revises: 0007_cmd_acct
Create Date: 2026-01-08
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0008_tacacs"
down_revision = "0007_cmd_acct"
branch_labels = None
depends_on = None

_ENUM = sa.Enum("radius", "tacacs", native_enum=False, length=16)


def _grant(verb: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return
    db = bind.engine.url.database
    user = os.environ.get("RADIUS_DB_USER", "radius_svc")
    if not user.replace("_", "").replace("-", "").isalnum():
        raise ValueError(f"RADIUS_DB_USER inválido: {user!r}")
    prep = "TO" if verb == "GRANT" else "FROM"
    bind.exec_driver_sql(
        f"{verb} SELECT ON `{db}`.`app_privilege_profile` {prep} '{user}'@'%%'"
    )


def upgrade() -> None:
    op.add_column(
        "app_manufacturer",
        sa.Column("aaa_protocol", _ENUM, nullable=False, server_default="radius"),
    )
    op.add_column("app_manufacturer", sa.Column("tacacs_key_enc", sa.String(512), nullable=True))
    op.add_column("app_equipment", sa.Column("aaa_protocol", _ENUM, nullable=True))
    op.add_column("app_equipment", sa.Column("tacacs_key_enc", sa.String(512), nullable=True))
    op.add_column(
        "app_privilege_profile",
        sa.Column("tacacs_priv_level", sa.Integer, nullable=False, server_default="1"),
    )
    op.add_column(
        "app_privilege_profile", sa.Column("tacacs_extra_avpairs", sa.Text, nullable=True)
    )
    # Backfill dos perfis internos (instalações que já existiam antes desta versão).
    for name, lvl in (("admin-full", 15), ("operator", 10), ("read-only", 1)):
        op.execute(
            sa.text("UPDATE app_privilege_profile SET tacacs_priv_level = :l WHERE name = :n")
            .bindparams(l=lvl, n=name)
        )
    _grant("GRANT")


def downgrade() -> None:
    _grant("REVOKE")
    op.drop_column("app_privilege_profile", "tacacs_extra_avpairs")
    op.drop_column("app_privilege_profile", "tacacs_priv_level")
    op.drop_column("app_equipment", "tacacs_key_enc")
    op.drop_column("app_equipment", "aaa_protocol")
    op.drop_column("app_manufacturer", "tacacs_key_enc")
    op.drop_column("app_manufacturer", "aaa_protocol")
