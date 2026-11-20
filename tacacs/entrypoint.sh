#!/bin/sh
# tac_plus-ng + importador de accounting + watcher de reload (SIGHUP).
set -e

CFG=/etc/tac_plus-ng/tac_plus-ng.cfg
GEN=/etc/tacacs-shared/h2node.cfg
ACCT=/var/log/tac_plus-ng/acct.log
ACCESS=/var/log/tac_plus-ng/access.log

mkdir -p /etc/tacacs-shared /var/log/tac_plus-ng
# O backend (uid diferente) escreve o h2node.cfg neste volume compartilhado.
chmod 0777 /etc/tacacs-shared
# Instalações de antes do rebranding: o painel gravava pulse.cfg. Aproveita o
# arquivo até o backend regravar o h2node.cfg (feito a cada start do backend).
LEGACY_GEN=/etc/tacacs-shared/pulse.cfg
if [ ! -s "$GEN" ] && [ -s "$LEGACY_GEN" ]; then
  echo "[h2node-tacacs] migrando $LEGACY_GEN -> $GEN"
  cp -p "$LEGACY_GEN" "$GEN"
fi
# Stub vazio no 1º boot — o painel sobrescreve com hosts + profiles + ruleset.
[ -f "$GEN" ] || : > "$GEN"
: >> "$ACCT"
: >> "$ACCESS"

echo "[h2node-tacacs] validando configuração..."
if ! /opt/tacplus/sbin/tac_plus-ng -P "$CFG" 2>&1; then
  echo "[h2node-tacacs] config gerada inválida — zerando $GEN e tentando de novo." >&2
  : > "$GEN"
  /opt/tacplus/sbin/tac_plus-ng -P "$CFG"
fi
echo "[h2node-tacacs] OK."

# Importador de accounting: segue o log e grava em cmd_acct.
( tail -n0 -F "$ACCT" | /usr/bin/python3 /opt/h2node/acct_import.py ) &

# Importador de autenticação: segue o access.log e grava as tentativas de
# login de shell em radpostauth (protocol='tacacs') — tela Authentication.
( tail -n0 -F "$ACCESS" | /usr/bin/python3 /opt/h2node/authlog_import.py ) &

# Watcher: quando o painel regrava h2node.cfg (rename atômico), recarrega o daemon.
# Observa o DIRETÓRIO — sobrevive ao os.replace() que troca o inode do arquivo.
(
  while inotifywait -qq -e close_write -e moved_to -e create /etc/tacacs-shared 2>/dev/null; do
    sleep 0.3
    pid=$(pidof tac_plus-ng | tr ' ' '\n' | sort -n | head -1)
    [ -n "$pid" ] && { echo "[h2node-tacacs] reload (SIGHUP $pid)"; kill -HUP "$pid"; }
  done
) &

exec /opt/tacplus/sbin/tac_plus-ng -f "$CFG"
