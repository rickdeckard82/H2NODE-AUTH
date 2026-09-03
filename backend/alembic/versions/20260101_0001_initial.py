"""schema inicial da aplicação (tabelas app_*)

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

ROLE = sa.Enum(
    "superadmin", "admin", "operator", "auditor",
    name="systemrole", native_enum=False, length=20,
)
MFR = sa.Enum(
    "huawei", "juniper", "datacom", "mikrotik",
    name="manufacturername", native_enum=False, length=20,
)
EQ_STATUS = sa.Enum(
    "active", "maintenance", "disabled",
    name="equipmentstatus", native_enum=False, length=16,
)


def upgrade() -> None:
    op.create_table(
        "app_system_user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(190), nullable=False, unique=True),
        sa.Column("full_name", sa.String(190), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", ROLE, nullable=False, server_default="operator"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("mfa_secret", sa.String(255)),
        sa.Column("last_login_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "app_manufacturer",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", MFR, nullable=False, unique=True),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("radius_vendor_id", sa.Integer),
        sa.Column("notes", sa.String(255)),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "app_privilege_profile",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.String(255)),
        sa.Column("is_builtin", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "app_privilege_profile_attr",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "profile_id", sa.Integer,
            sa.ForeignKey("app_privilege_profile.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "manufacturer_id", sa.Integer,
            sa.ForeignKey("app_manufacturer.id"), nullable=False,
        ),
        sa.Column("attribute", sa.String(64), nullable=False),
        sa.Column("op", sa.String(2), nullable=False, server_default=":="),
        sa.Column("value", sa.String(253), nullable=False),
        sa.UniqueConstraint("profile_id", "manufacturer_id", "attribute", name="uq_profile_attr"),
    )

    op.create_table(
        "app_equipment",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, index=True),
        sa.Column("mgmt_ip", sa.String(45), nullable=False, unique=True),
        sa.Column("manufacturer_id", sa.Integer, sa.ForeignKey("app_manufacturer.id"), nullable=False),
        sa.Column("model", sa.String(120)),
        sa.Column("site", sa.String(120)),
        sa.Column("shortname", sa.String(32), nullable=False),
        sa.Column("radius_secret_enc", sa.String(512), nullable=False),
        sa.Column("coa_port", sa.Integer, nullable=False, server_default="3799"),
        sa.Column("status", EQ_STATUS, nullable=False, server_default="active"),
        sa.Column("description", sa.String(255)),
        sa.Column(
            "created_by", sa.Integer,
            sa.ForeignKey("app_system_user.id", ondelete="SET NULL"),
        ),
        sa.Column("last_seen_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "app_auth_user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("full_name", sa.String(190)),
        sa.Column("email", sa.String(190)),
        sa.Column(
            "privilege_profile_id", sa.Integer,
            sa.ForeignKey("app_privilege_profile.id"), nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("expires_at", sa.DateTime),
        sa.Column("last_auth_at", sa.DateTime),
        sa.Column(
            "created_by", sa.Integer,
            sa.ForeignKey("app_system_user.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "app_audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("actor_system_user_id", sa.Integer),
        sa.Column("actor_username", sa.String(64)),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("entity_type", sa.String(48), nullable=False),
        sa.Column("entity_id", sa.String(64)),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(255)),
        sa.Column("before_json", sa.Text),
        sa.Column("after_json", sa.Text),
    )

    op.create_table(
        "app_refresh_token",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("jti", sa.String(32), nullable=False, unique=True),
        sa.Column(
            "system_user_id", sa.Integer,
            sa.ForeignKey("app_system_user.id", ondelete="CASCADE"), nullable=False, index=True,
        ),
        sa.Column("issued_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("replaced_by_jti", sa.String(32)),
        sa.Column("user_agent", sa.String(255)),
        sa.Column("ip_address", sa.String(45)),
    )


def downgrade() -> None:
    for tbl in (
        "app_refresh_token", "app_audit_log", "app_auth_user", "app_equipment",
        "app_privilege_profile_attr", "app_privilege_profile", "app_manufacturer",
        "app_system_user",
    ):
        op.drop_table(tbl)
