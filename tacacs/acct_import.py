#!/usr/bin/python3
"""Importa o log de accounting do tac_plus-ng para a tabela cmd_acct.

Recebe as linhas no stdin (via `tail -n0 -F /var/log/tac_plus-ng/acct.log`).
Formato definido em tac_plus-ng.cfg (accounting format), campos separados por TAB:

    <ISO-8601>  <accttype>  <session_id>  <nas>  <user>  <nac>  <port>  <service>  <cmd + args>

`accttype` ∈ start | stop | update. Comandos de shell chegam em `cmd` com
`accttype=update`; start/stop de exec chegam com `cmd` vazio.

Muitos NAS só enviam `nac` (rem_addr — IP de quem conectou) no pacote de
`start`; os `update` de cada comando chegam com `nac` vazio. `session_id`
(cabeçalho TACACS+, constante durante toda a sessão) permite reaproveitar o
último `nac` visto naquela sessão para preencher os `update` sem IP próprio.
"""

import datetime
import os
import sys
import time

import pymysql

# session_id -> último nac (rem_addr) não vazio visto nessa sessão.
_NAC_CACHE: dict[str, str] = {}
_NAC_CACHE_MAX = 5000

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
    if len(f) < 8:
        return None
    ts_raw = f[0]
    # Tolera o prefixo padrão "YYYY-mm-dd HH:MM:SS +0000 " caso o override de prefix falhe.
    if "T" not in ts_raw and " " in ts_raw:
        first = ts_raw.split(" ")[0]
        ts_raw = first + "T00:00:00"
    accttype, session_id, nas, user, nac, port, service = (f[1:8] + [""] * 7)[:7]
    if nac in ("0.0.0.0", "::", "0:0:0:0:0:0:0:0"):
        nac = ""
    cmd = "\t".join(f[8:]).strip() if len(f) > 8 else ""
    try:
        event_time = datetime.datetime.fromisoformat(ts_raw.split("+")[0].rstrip("Z"))
    except ValueError:
        event_time = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    if cmd:
        action, command = "cmd", cmd[:512]
    else:
        action, command = f"exec-{accttype or 'update'}", (service or "")[:512]

    if session_id:
        if nac:
            if len(_NAC_CACHE) >= _NAC_CACHE_MAX:
                _NAC_CACHE.pop(next(iter(_NAC_CACHE)))
            _NAC_CACHE[session_id] = nac
        else:
            nac = _NAC_CACHE.get(session_id, "")
        if accttype == "stop":
            _NAC_CACHE.pop(session_id, None)

    return (event_time, nas[:15], user[:64], nac[:50], action[:32], command, session_id[:64])


def main() -> None:
    global _conn
    # um byte que não é UTF-8 (ex.: num comando digitado no equipamento) não
    # pode derrubar o importador — nada o reinicia sozinho
    sys.stdin.reconfigure(errors="replace")
    for line in sys.stdin:
        try:
            row = parse(line)
        except Exception as exc:  # noqa: BLE001 - linha ruim: registra e segue
            sys.stderr.write(f"acct_import: linha ignorada ({exc}): {line[:200]!r}\n")
            sys.stderr.flush()
            continue
        if row is None:
            continue
        for attempt in (1, 2):
            try:
                with _cursor() as cur:
                    cur.execute(_INSERT, row)
                break
            except Exception as exc:  # noqa: BLE001 - o loop nunca morre
                _conn = None
                if attempt == 2:
                    sys.stderr.write(f"acct_import: {exc}\n")
                    sys.stderr.flush()
                else:
                    time.sleep(0.3)


if __name__ == "__main__":
    main()
