#!/usr/bin/python3
"""Importa as tentativas de login do access.log do tac_plus-ng para radpostauth.

Recebe as linhas no stdin (via `tail -n0 -F /var/log/tac_plus-ng/access.log`),
irmão do acct_import.py. Assim as autenticações TACACS+ aparecem na mesma tela
"Authentication" do painel que as do RADIUS, com `protocol = 'tacacs'`.

Formato padrão da linha de acesso do tac_plus-ng (campos separados por TAB, e o
1º campo com espaços):

    <YYYY-mm-dd> <HH:MM:SS> <+ZZZZ> <nas-ip>  <user>  <port>  <rem-addr>  <msg>

Só interessam as linhas de autenticação de shell — `<msg>` == "shell login
succeeded" / "shell login failed". As linhas de autorização (com grupo/permit/
comando) são ignoradas aqui (vão para cmd_acct via acct_import.py).
"""

import datetime
import os
import sys
import time

import pymysql

_DB = dict(
    host=os.getenv("SQL_HOST", "db"),
    port=int(os.getenv("SQL_PORT", "3306")),
    user=os.getenv("SQL_USER", "radius_svc"),
    password=os.getenv("SQL_PASSWORD", ""),
    database=os.getenv("SQL_DB", "radius"),
    autocommit=True,
    connect_timeout=5,
)

_INSERT = (
    "INSERT INTO radpostauth "
    "(username, pass, reply, authdate, nasipaddress, serveripaddress, protocol) "
    "VALUES (%s, '', %s, %s, %s, NULL, 'tacacs')"
)

# Este servidor (opcional) — preenche o "IP de destino" das linhas TACACS+.
_SERVER_IP = os.getenv("TACACS_SERVER_IP") or None
if _SERVER_IP:
    _INSERT = (
        "INSERT INTO radpostauth "
        "(username, pass, reply, authdate, nasipaddress, serveripaddress, protocol) "
        "VALUES (%s, '', %s, %s, %s, %s, 'tacacs')"
    )

_conn = None


def _cursor():
    global _conn
    if _conn is None:
        _conn = pymysql.connect(**_DB)
    return _conn.cursor()


def parse(line: str) -> tuple | None:
    f = line.rstrip("\n").split("\t")
    if len(f) < 5:
        return None
    msg = f[-1].strip()
    if msg == "shell login succeeded":
        reply = "Access-Accept"
    elif msg == "shell login failed":
        reply = "Access-Reject"
    else:
        return None  # linha de autorização / outro evento

    head = f[0].split()  # <date> <time> <tz> <nas-ip>
    if len(head) < 2:
        return None
    nas_ip = head[-1] if len(head) >= 4 else ""
    ts_raw = f"{head[0]}T{head[1]}"
    try:
        authdate = datetime.datetime.fromisoformat(ts_raw)
    except ValueError:
        authdate = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

    username = (f[1] if len(f) > 1 else "")[:64]
    row = [username, reply, authdate, nas_ip[:45]]
    if _SERVER_IP:
        row.append(_SERVER_IP[:45])
    return tuple(row)


def main() -> None:
    global _conn
    for line in sys.stdin:
        row = parse(line)
        if row is None:
            continue
        for attempt in (1, 2):
            try:
                with _cursor() as cur:
                    cur.execute(_INSERT, row)
                break
            except pymysql.Error as exc:
                _conn = None
                if attempt == 2:
                    sys.stderr.write(f"authlog_import: {exc}\n")
                    sys.stderr.flush()
                else:
                    time.sleep(0.3)


if __name__ == "__main__":
    main()
