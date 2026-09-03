"""tabela cmd_acct — contabilização de comandos executados nos equipamentos

O FreeRADIUS grava aqui (site `default`, seção accounting) quando um pacote de
Accounting traz o comando num VSA de fabricante. Alimenta as telas Authorization
e Accounting do painel.

Fora do autogenerate (env.py: RADIUS_TABLES) — como as tabelas rad*. Também é
criada em db/init/00_radius_schema.sql para instalações novas; esta migração
cobre os ambientes já existentes. Guardada para mysql (testes usam SQLite via
Base.metadata.create_all).

Revision ID: 0007_cmd_acct
Revises: 0006_system_user_timezone
Create Date: 2026-01-07
"""

import os

from alembic import op

revision = "0007_cmd_acct"
down_revision = "0006_system_user_timezone"
branch_labels = None
depends_on = None

_DDL = """
CREATE TABLE IF NOT EXISTS cmd_acct (
  id               bigint(21)   NOT NULL AUTO_INCREMENT,
  event_time       datetime     NOT NULL,
  nasipaddress     varchar(15)  NOT NULL DEFAULT '',
  username         varchar(64)  NOT NULL DEFAULT '',
  callingstationid varchar(50)  NOT NULL DEFAULT '',
  action           varchar(32)  NOT NULL DEFAULT '',
  command          varchar(512) NOT NULL DEFAULT '',
  acctsessionid    varchar(64)  NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  KEY username (username(32)),
  KEY event_time (event_time),
  KEY nasipaddress (nasipaddress)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def _radius_user() -> str:
    name = os.environ.get("RADIUS_DB_USER", "radius_svc")
    if not name.replace("_", "").replace("-", "").isalnum():
        raise ValueError(f"RADIUS_DB_USER inválido: {name!r}")
    return name


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return
    db = bind.engine.url.database
    bind.exec_driver_sql(_DDL)
    bind.exec_driver_sql(
        f"GRANT SELECT, INSERT ON `{db}`.`cmd_acct` TO '{_radius_user()}'@'%%'"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return
    db = bind.engine.url.database
    bind.exec_driver_sql(f"REVOKE SELECT, INSERT ON `{db}`.`cmd_acct` FROM '{_radius_user()}'@'%%'")
    bind.exec_driver_sql("DROP TABLE IF EXISTS cmd_acct")
