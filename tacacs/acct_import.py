#!/usr/bin/python3
"""Importa o log de accounting do tac_plus-ng para a tabela cmd_acct.

Recebe as linhas no stdin (via `tail -n0 -F /var/log/tac_plus-ng/acct.log`).
Formato definido em tac_plus-ng.cfg (accounting format), campos separados por TAB:

    <ISO-8601>  <accttype>  <nas>  <user>  <nac>  <port>  <service>  <cmd + args>

`accttype` ∈ start | stop | update. Comandos de shell chegam em `cmd` com
`accttype=update`; start/stop de exec chegam com `cmd` vazio.
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
    "INSERT INTO cmd_acct "
    "(event_time, nasipaddress, username, callingstationid, action, command, acctsessionid) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)

_conn = None


def _cursor():
    global _conn
    if _conn is None:
        _conn = pymysql.connect(**_DB)
    return _conn.cursor()


def parse(line: str) -> tuple | None:
    f = line.rstrip("\n").split("\t")
    if len(f) < 7:
        return None
    ts_raw = f[0]
    # Tolera o prefixo padrão "YYYY-mm-dd HH:MM:SS +0000 " caso o override de prefix falhe.
    if "T" not in ts_raw and " " in ts_raw:
        first = ts_raw.split(" ")[0]
        ts_raw = first + "T00:00:00"
    accttype, nas, user, nac, port, service = (f[1:7] + [""] * 6)[:6]
    cmd = "\t".join(f[7:]).strip() if len(f) > 7 else ""
    try:
        event_time = datetime.datetime.fromisoformat(ts_raw.split("+")[0].rstrip("Z"))
    except ValueError:
        event_time = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    if cmd:
        action, command = "cmd", cmd[:512]
    else:
        action, command = f"exec-{accttype or 'update'}", (service or "")[:512]
    return (event_time, nas[:15], user[:64], nac[:50], action[:32], command, "")


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
                    sys.stderr.write(f"acct_import: {exc}\n")
                    sys.stderr.flush()
                else:
                    time.sleep(0.3)


if __name__ == "__main__":
    main()
