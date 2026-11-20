#!/usr/bin/env bash
# Restore drill: prova de verdade que o ÚLTIMO backup gerado pelo serviço
# `db-backup` restaura com sucesso. Sobe um MySQL efêmero e isolado (nunca
# toca no `db` real), aplica o dump mais recente, valida com queries de
# sanidade e destrói tudo ao final — sucesso/falha vai no exit code, para
# rodar em cron e alertar se quebrar.
#
# Uso:
#   ./scripts/restore_drill.sh              # usa o volume db_backups do compose
#   ./scripts/restore_drill.sh /caminho.sql  # testa um arquivo específico
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DRILL_NAME="h2node-auth-restore-drill-$$"
DRILL_NET="${DRILL_NAME}-net"
DRILL_ROOT_PASSWORD="drill-$$-$(date +%s)"

# shellcheck disable=SC1091
# exporta (não só atribui) para o openssl/subprocessos enxergarem via `env:VAR`
set -a
[ -f .env ] && source <(grep -E '^BACKUP_ENCRYPTION_KEY=' .env || true)
set +a

cleanup() {
  docker rm -f "$DRILL_NAME" >/dev/null 2>&1 || true
  docker network rm "$DRILL_NET" >/dev/null 2>&1 || true
  [ -n "${TMP_SQL:-}" ] && rm -f "$TMP_SQL"
}
trap cleanup EXIT

echo "[restore-drill] localizando o backup a testar..."
if [ "${1:-}" != "" ]; then
  SRC="$1"
  COPY_FROM_VOLUME=false
else
  VOLUME="$(docker volume ls --filter name=db_backups --format '{{.Name}}' | head -n1)"
  if [ -z "$VOLUME" ]; then
    echo "[restore-drill] nenhum volume *db_backups* encontrado — suba o serviço db-backup primeiro." >&2
    exit 2
  fi
  LATEST="$(docker run --rm -v "$VOLUME":/backups:ro alpine \
    sh -c 'ls -1t /backups/*.sql /backups/*.sql.enc 2>/dev/null | head -n1')"
  if [ -z "$LATEST" ]; then
    echo "[restore-drill] volume $VOLUME está vazio — nenhum backup para testar." >&2
    exit 2
  fi
  SRC="$LATEST"
  COPY_FROM_VOLUME=true
  DRILL_VOLUME="$VOLUME"
fi
echo "[restore-drill] alvo: $SRC"

TMP_SQL="$(mktemp /tmp/h2node-auth-restore-drill.XXXXXX.sql)"

if $COPY_FROM_VOLUME; then
  extract_cmd="cat \"$SRC\""
  if [[ "$SRC" == *.enc ]]; then
    [ -n "${BACKUP_ENCRYPTION_KEY:-}" ] || {
      echo "[restore-drill] backup está cifrado mas BACKUP_ENCRYPTION_KEY não está no .env" >&2
      exit 2
    }
    extract_cmd="openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in \"$SRC\" -pass env:BACKUP_ENCRYPTION_KEY"
  fi
  docker run --rm -v "$DRILL_VOLUME":/backups:ro -e BACKUP_ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}" \
    alpine sh -c "apk add --no-cache openssl >/dev/null 2>&1; $extract_cmd" > "$TMP_SQL"
else
  if [[ "$SRC" == *.enc ]]; then
    [ -n "${BACKUP_ENCRYPTION_KEY:-}" ] || {
      echo "[restore-drill] arquivo cifrado mas BACKUP_ENCRYPTION_KEY não está no .env" >&2
      exit 2
    }
    openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in "$SRC" -pass "env:BACKUP_ENCRYPTION_KEY" > "$TMP_SQL"
  else
    cp "$SRC" "$TMP_SQL"
  fi
fi

if [ ! -s "$TMP_SQL" ]; then
  echo "[restore-drill] dump extraído está vazio — falha na decifragem ou backup corrompido." >&2
  exit 1
fi

echo "[restore-drill] subindo MySQL efêmero para o teste..."
docker network create "$DRILL_NET" >/dev/null
docker run -d --name "$DRILL_NAME" --network "$DRILL_NET" \
  --tmpfs /var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD="$DRILL_ROOT_PASSWORD" \
  mysql:8.4 >/dev/null

echo -n "[restore-drill] aguardando o MySQL efêmero ficar pronto"
for _ in $(seq 1 60); do
  if docker exec "$DRILL_NAME" mysqladmin ping -h 127.0.0.1 -p"$DRILL_ROOT_PASSWORD" --silent >/dev/null 2>&1; then
    echo " ok"
    break
  fi
  echo -n "."
  sleep 2
done

echo "[restore-drill] aplicando o dump..."
# db-backup usa `mysqldump ... radius` (sem --databases): o dump não cria o
# schema, então criamos aqui antes de aplicar — igual ao procedimento real de
# restauração documentado no RUNBOOK.
docker exec "$DRILL_NAME" mysql -u root -p"$DRILL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS radius" >/dev/null
if ! docker exec -i "$DRILL_NAME" mysql -u root -p"$DRILL_ROOT_PASSWORD" radius < "$TMP_SQL"; then
  echo "[restore-drill] FALHA: a restauração não aplicou o dump com sucesso." >&2
  exit 1
fi

echo "[restore-drill] validando com queries de sanidade..."
CHECKS_OK=true
check() {
  local desc="$1" sql="$2" min="$3"
  local val
  val="$(docker exec "$DRILL_NAME" mysql -N -u root -p"$DRILL_ROOT_PASSWORD" radius -e "$sql" 2>/dev/null || echo -1)"
  if [ "$val" -ge "$min" ] 2>/dev/null; then
    echo "  [ok] $desc = $val"
  else
    echo "  [FALHA] $desc = $val (esperado >= $min)"
    CHECKS_OK=false
  fi
}
check "tabelas no schema" "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='radius'" 10
check "app_system_user"   "SELECT COUNT(*) FROM app_system_user" 1
check "app_manufacturer"  "SELECT COUNT(*) FROM app_manufacturer" 1
check "radcheck (tabela existe)" "SELECT COUNT(*) FROM radcheck" 0
check "nas (tabela existe)"      "SELECT COUNT(*) FROM nas" 0

if $CHECKS_OK; then
  echo "[restore-drill] SUCESSO: o backup restaura e passa nas validações de sanidade."
  exit 0
else
  echo "[restore-drill] FALHA: restaurou, mas alguma validação de sanidade não passou." >&2
  exit 1
fi
