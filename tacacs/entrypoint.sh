#!/bin/sh
# tac_plus-ng + importador de accounting + watcher de reload (SIGHUP).
set -e

CFG=/etc/tac_plus-ng/tac_plus-ng.cfg
GEN=/etc/tacacs-shared/pulse.cfg
ACCT=/var/log/tac_plus-ng/acct.log

mkdir -p /etc/tacacs-shared /var/log/tac_plus-ng
# O backend (uid diferente) escreve o pulse.cfg neste volume compartilhado.
chmod 0777 /etc/tacacs-shared
# Stub vazio no 1º boot — o painel sobrescreve com hosts + profiles + ruleset.
[ -f "$GEN" ] || : > "$GEN"
: >> "$ACCT"

echo "[pulse-tacacs] validando configuração..."
if ! /opt/tacplus/sbin/tac_plus-ng -P "$CFG" 2>&1; then
  echo "[pulse-tacacs] config gerada inválida — zerando $GEN e tentando de novo." >&2
  : > "$GEN"
  /opt/tacplus/sbin/tac_plus-ng -P "$CFG"
fi
echo "[pulse-tacacs] OK."

# Importador de accounting: segue o log e grava em cmd_acct.
( tail -n0 -F "$ACCT" | /usr/bin/python3 /opt/pulse/acct_import.py ) &

# Watcher: quando o painel regrava pulse.cfg (rename atômico), recarrega o daemon.
# Observa o DIRETÓRIO — sobrevive ao os.replace() que troca o inode do arquivo.
(
  while inotifywait -qq -e close_write -e moved_to -e create /etc/tacacs-shared 2>/dev/null; do
    sleep 0.3
    pid=$(pidof tac_plus-ng | tr ' ' '\n' | sort -n | head -1)
    [ -n "$pid" ] && { echo "[pulse-tacacs] reload (SIGHUP $pid)"; kill -HUP "$pid"; }
  done
) &

exec /opt/tacplus/sbin/tac_plus-ng -f "$CFG"
