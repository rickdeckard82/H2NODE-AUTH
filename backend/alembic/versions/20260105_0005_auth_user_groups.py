"""grupos de usuário de autenticação com allowlist de IP de origem

Revision ID: 0005_auth_user_groups
Revises: 0004_radius_svc_grants
Create Date: 2026-01-05
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0005_auth_user_groups"
down_revision = "0004_radius_svc_grants"
branch_labels = None
depends_on = None


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
        f"{verb} SELECT ON `{db}`.`app_auth_group_cidr` {prep} '{user}'@'%%'"
    )


def upgrade() -> None:
    op.create_table(
        "app_auth_user_group",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.String(255)),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "app_auth_group_cidr",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "group_id", sa.Integer,
            sa.ForeignKey("app_auth_user_group.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("cidr", sa.String(64), nullable=False),
        sa.Column("family", sa.Integer, nullable=False),
        sa.Column("ip_start", sa.LargeBinary(16), nullable=False),
        sa.Column("ip_end", sa.LargeBinary(16), nullable=False),
        sa.Column("note", sa.String(120)),
    )
    op.add_column(
        "app_auth_user",
        sa.Column(
            "auth_group_id", sa.Integer,
            sa.ForeignKey("app_auth_user_group.id", ondelete="SET NULL"), nullable=True,
        ),
    )
    _grant("GRANT")


def downgrade() -> None:
    _grant("REVOKE")
    op.drop_column("app_auth_user", "auth_group_id")
    op.drop_table("app_auth_group_cidr")
    op.drop_table("app_auth_user_group")
