"""concede ao radius_svc SELECT nas tabelas app_* que o FreeRADIUS consulta

As tabelas app_auth_user / app_equipment / app_manufacturer só existem depois do
Alembic, então o grant não cabe no db/init. Roda como backend_svc (que tem
WITH GRANT OPTION em radius.*). Idempotente e tolerante a ambientes sem MySQL
(ex.: testes em SQLite).

Revision ID: 0004_radius_svc_grants
Revises: 0003_login_lockout
Create Date: 2026-01-04
"""

import os

from alembic import op

revision = "0004_radius_svc_grants"
down_revision = "0003_login_lockout"
branch_labels = None
depends_on = None

_TABLES = ("app_auth_user", "app_equipment", "app_manufacturer")


def _radius_user() -> str:
    # nome simples validado; evita interpolação perigosa no GRANT
    name = os.environ.get("RADIUS_DB_USER", "radius_svc")
    if not name.replace("_", "").replace("-", "").isalnum():
        raise ValueError(f"RADIUS_DB_USER inválido: {name!r}")
    return name


def _run(verb: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return
    db = bind.engine.url.database
    user = _radius_user()
    prep = "TO" if verb == "GRANT" else "FROM"
    for t in _TABLES:
        # `%%` -> `%` após o processamento do driver pymysql.
        # GRANT/REVOKE já recarregam os privilégios; não precisa de FLUSH.
        bind.exec_driver_sql(f"{verb} SELECT ON `{db}`.`{t}` {prep} '{user}'@'%%'")


def upgrade() -> None:
    _run("GRANT")


def downgrade() -> None:
    _run("REVOKE")
