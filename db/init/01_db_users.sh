#!/bin/bash
# Cria os usuários de serviço com privilégio mínimo.
# Executado uma única vez pelo entrypoint do MySQL, que faz `source` deste
# arquivo — por isso NÃO usamos `set -e`/`set -u` aqui (vazariam para o
# entrypoint). Erros são tratados explicitamente.

_pr_db="${MYSQL_DATABASE:-radius}"

mysql --protocol=socket -uroot -p"${MYSQL_ROOT_PASSWORD}" <<-EOSQL || { echo "[init] FALHA ao criar usuários de serviço" >&2; exit 1; }
  -- ── backend_svc: CRUD completo no schema da aplicação e nas tabelas RADIUS ──
  -- WITH GRANT OPTION: a migração 0004 usa esta conta para conceder ao
  -- radius_svc o SELECT nas tabelas app_* que só existem após o Alembic.
  CREATE USER IF NOT EXISTS '${MYSQL_BACKEND_USER}'@'%' IDENTIFIED BY '${MYSQL_BACKEND_PASSWORD}';
  GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES, DROP, CREATE TEMPORARY TABLES
    ON \`${_pr_db}\`.* TO '${MYSQL_BACKEND_USER}'@'%' WITH GRANT OPTION;

  -- ── radius_svc: privilégio mínimo para o FreeRADIUS ──
  -- SÓ as tabelas que o servidor lê. NÃO tem acesso a app_system_user,
  -- app_refresh_token nem app_audit_log. O SELECT em app_auth_user /
  -- app_equipment / app_manufacturer é concedido pela migração 0004.
  CREATE USER IF NOT EXISTS '${MYSQL_RADIUS_USER}'@'%' IDENTIFIED BY '${MYSQL_RADIUS_PASSWORD}';
  GRANT SELECT ON \`${_pr_db}\`.radcheck       TO '${MYSQL_RADIUS_USER}'@'%';
  GRANT SELECT ON \`${_pr_db}\`.radreply       TO '${MYSQL_RADIUS_USER}'@'%';
  GRANT SELECT ON \`${_pr_db}\`.radgroupcheck  TO '${MYSQL_RADIUS_USER}'@'%';
  GRANT SELECT ON \`${_pr_db}\`.radgroupreply  TO '${MYSQL_RADIUS_USER}'@'%';
  GRANT SELECT ON \`${_pr_db}\`.radusergroup   TO '${MYSQL_RADIUS_USER}'@'%';
  GRANT SELECT ON \`${_pr_db}\`.nas            TO '${MYSQL_RADIUS_USER}'@'%';
  GRANT SELECT, INSERT, UPDATE, DELETE ON \`${_pr_db}\`.radacct     TO '${MYSQL_RADIUS_USER}'@'%';
  GRANT SELECT, INSERT, UPDATE, DELETE ON \`${_pr_db}\`.radpostauth TO '${MYSQL_RADIUS_USER}'@'%';
  GRANT INSERT, UPDATE, DELETE         ON \`${_pr_db}\`.nasreload   TO '${MYSQL_RADIUS_USER}'@'%';
  GRANT SELECT, INSERT                 ON \`${_pr_db}\`.cmd_acct    TO '${MYSQL_RADIUS_USER}'@'%';

  FLUSH PRIVILEGES;
EOSQL

echo "[init] usuários ${MYSQL_BACKEND_USER} e ${MYSQL_RADIUS_USER} criados."
