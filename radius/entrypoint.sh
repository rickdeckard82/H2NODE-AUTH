#!/bin/sh
# O compose já garante (depends_on: condition: service_healthy) que o MySQL
# está pronto antes deste container iniciar. Ainda assim damos uma folga curta
# para o handshake do driver e validamos a config antes de subir.
set -e

sleep 3

echo "[h2node-auth] validando configuração do FreeRADIUS..."
if ! freeradius -C -l stdout; then
  echo "[h2node-auth] configuração inválida (veja acima). Abortando." >&2
  exit 1
fi
echo "[h2node-auth] configuração OK. Iniciando."

exec "$@"
