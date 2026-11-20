#!/usr/bin/env bash
# Migra um servidor que roda o Pulse RADIUS (projeto compose "pulse-radius") para o
# H2NODE Auth sem perder nada: banco (usuários, equipamentos, perfis, accounting),
# backups locais, logs e a config gerada do TACACS+ ficam onde estão.
#
#   ./scripts/migrar-h2node.sh          mostra o que vai fazer e pede confirmação
#   ./scripts/migrar-h2node.sh -y       sem perguntar
#
# Rode como root (ou usuário no grupo docker), na pasta do repositório (onde está o
# .env), DEPOIS do git pull. Idempotente: rodar de novo não muda nada.
#
# Os equipamentos só ficam sem resposta entre o "down" do projeto antigo e o "up" do
# novo (freeradius e tacacs usam a rede do host: os dois projetos não sobem juntos).
set -euo pipefail

YES=0
[ "${1:-}" = "-y" ] && YES=1
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "não achei o .env nesta pasta ($(pwd))" >&2; exit 1; }
command -v docker >/dev/null || { echo "docker não instalado" >&2; exit 1; }

LEGACY=pulse-radius
NEW=h2node-auth
envval() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2-; }
has_volume() { docker volume inspect "$1" >/dev/null 2>&1; }
old_containers() { docker ps -aq --filter "label=com.docker.compose.project=$LEGACY"; }

plan=()
add_env=()

# 1. Volumes: continuar usando os do projeto antigo (o docker-compose.yml agora fixa
#    o nome como ${VOLUME_PREFIX}_db_data etc.).
if [ -z "$(envval VOLUME_PREFIX)" ]; then
    if has_volume "${LEGACY}_db_data"; then
        add_env+=("VOLUME_PREFIX=$LEGACY")
        plan+=("usar os volumes existentes ${LEGACY}_* (banco, backups, logs, config do TACACS+)")
    else
        add_env+=("VOLUME_PREFIX=$NEW")
    fi
elif [ "$(envval VOLUME_PREFIX)" != "$LEGACY" ] && has_volume "${LEGACY}_db_data" \
        && ! has_volume "$(envval VOLUME_PREFIX)_db_data"; then
    echo "AVISO: o .env tem VOLUME_PREFIX=$(envval VOLUME_PREFIX), mas o banco atual está em" >&2
    echo "       ${LEGACY}_db_data. Subir assim cria um banco VAZIO. Corrija o .env" >&2
    echo "       (VOLUME_PREFIX=$LEGACY) e rode de novo." >&2
    exit 1
fi

# 2. Containers do projeto antigo saem (os volumes ficam)
if [ -n "$(old_containers)" ]; then
    plan+=("parar e remover os containers do projeto \"$LEGACY\" (docker compose -p $LEGACY down — sem -v)")
fi
plan+=("subir a stack como projeto \"$NEW\" (docker compose up -d --build)")

echo "Migração Pulse RADIUS → H2NODE Auth em $(pwd):"
for p in "${plan[@]}"; do echo "  • $p"; done
for e in "${add_env[@]}"; do echo "  • acrescentar ao .env: $e"; done
echo
if [ "$YES" -ne 1 ]; then
    read -r -p "Continuar? [s/N] " r
    case "$r" in s|S|sim|SIM) ;; *) echo "nada feito."; exit 0 ;; esac
fi

if [ "${#add_env[@]}" -gt 0 ]; then
    cp -p .env ".env.antes-h2node.$(date +%Y%m%d%H%M%S)"
    { echo; echo "# acrescentado por scripts/migrar-h2node.sh"; printf '%s\n' "${add_env[@]}"; } >> .env
fi

if [ -n "$(old_containers)" ]; then
    docker compose -p "$LEGACY" down
fi
docker compose up -d --build

echo
echo "Pronto. Confira: docker compose ps   e   o painel no navegador."
echo "Teste um login RADIUS e um TACACS+ de um equipamento. Detalhes: docs/migracao-h2node.md."
