"""radius_svc: SELECT em app_privilege_profile (TACACS+/MAVIS)

O grant estava no db/init/01_db_users.sh, mas app_privilege_profile só existe
depois do Alembic: num volume novo o MySQL 8.4 recusava o GRANT (tabela
inexistente) e o init do banco falhava. Stacks criadas antes do TACACS+ nunca
rodaram essa linha. Mesmo padrão da 0004: roda como backend_svc (WITH GRANT
OPTION), idempotente e no-op fora do MySQL.

Revision ID: 0019_radius_svc_privprofile
Revises: 0018_backup_schedule
Create Date: 2026-10-19
"""

import os

from alembic import op

revision = "0019_radius_svc_privprofile"
down_revision = "0018_backup_schedule"
branch_labels = None
depends_on = None


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
    prep = "TO" if verb == "GRANT" else "FROM"
    # `%%` -> `%` após o processamento do driver pymysql.
    bind.exec_driver_sql(
        f"{verb} SELECT ON `{db}`.`app_privilege_profile` {prep} '{_radius_user()}'@'%%'"
    )


def upgrade() -> None:
    _run("GRANT")


def downgrade() -> None:
    _run("REVOKE")
