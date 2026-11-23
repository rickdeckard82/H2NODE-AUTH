#!/usr/bin/python3
"""MAVIS backend do H2NODE Auth — autenticação e lookup de grupo contra o MySQL do painel.

Protocolo MAVIS: linhas "<int> <valor>" no stdin terminadas por "=", resposta no
mesmo formato + "=<verdict>". Usa a lib mavis.py que vem com o tac_plus-ng.

Trata:
  TACTYPE=AUTH  -> verifica a senha (SSHA2-512 em radcheck) e o estado do
                   app_auth_user (is_active / expires_at); devolve TACMEMBER = nome
                   do perfil de privilégio.
  TACTYPE=INFO  -> devolve TACMEMBER = nome do perfil (autorização por profile no
                   ruleset gerado pelo painel).

Accounting NÃO passa por aqui — vai para o log e é importado pelo acct_import.py.
"""

import datetime
import ipaddress
import os
import sys
import time

import pymysql

sys.path.insert(0, "/opt/tacplus/lib/mavis")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mavis import (  # noqa: E402
    AV_A_IPADDR,
    AV_A_TACCLIENT,
    AV_V_RESULT_ERROR,
    AV_V_RESULT_FAIL,
    AV_V_RESULT_NOTFOUND,
    AV_V_RESULT_OK,
    MAVIS_DOWN,
    MAVIS_FINAL,
    Mavis,
)
from password import verify_ssha512  # noqa: E402

_DB = dict(
    host=os.getenv("SQL_HOST", "db"),
    port=int(os.getenv("SQL_PORT", "3306")),
    user=os.getenv("SQL_USER", "radius_svc"),
    password=os.getenv("SQL_PASSWORD", ""),
    database=os.getenv("SQL_DB", "radius"),
    autocommit=True,
    connect_timeout=5,
)

_conn: pymysql.connections.Connection | None = None


def _query(sql: str, args: tuple = ()) -> list:
    global _conn
    for attempt in (1, 2):
        try:
            if _conn is None:
                _conn = pymysql.connect(**_DB)
            with _conn.cursor() as cur:
                cur.execute(sql, args)
                return cur.fetchall()
        except pymysql.Error:
            _conn = None
            if attempt == 2:
                raise
            time.sleep(0.3)
    return []


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def lookup(username: str) -> tuple[bool | None, str | None, str | None, int | None]:
    """(estado_ok, nome_do_perfil, hash_ssha512, grupo). Perfil None => usuário inexistente."""
    rows = _query(
        "SELECT u.is_active, u.expires_at, p.name, u.auth_group_id "
        "FROM app_auth_user u JOIN app_privilege_profile p ON p.id = u.privilege_profile_id "
        "WHERE u.username = %s LIMIT 1",
        (username,),
    )
    if not rows:
        return (None, None, None, None)
    is_active, expires_at, pname, group_id = rows[0]
    ok = bool(is_active) and (expires_at is None or expires_at > _utcnow())
    h = _query(
        "SELECT value FROM radcheck WHERE username = %s AND attribute = 'SSHA2-512-Password' LIMIT 1",
        (username,),
    )
    return (ok, pname, h[0][0] if h else None, group_id)


def ip_allowed(group_id: int | None, ip: str | None) -> bool:
    """Mesma regra do RADIUS (sites-available/default): usuário com grupo só entra
    de um IP dentro de uma das faixas do grupo; sem grupo, de qualquer lugar."""
    if group_id is None:
        return True
    try:
        addr = ipaddress.ip_address((ip or "").strip())
    except ValueError:
        return False
    rows = _query(
        "SELECT family, ip_start, ip_end FROM app_auth_group_cidr WHERE group_id = %s",
        (group_id,),
    )
    # ip_start/ip_end têm o tamanho de addr.packed (INET6_ATON): comparar bytes = comparar IPs
    return any(
        fam == addr.version and bytes(lo) <= addr.packed <= bytes(hi) for fam, lo, hi in rows
    )


def main() -> None:
    while True:
        D = Mavis()
        if not D.is_tacplus():
            continue
        if not D.valid():
            continue

        try:
            ok_state, pname, ssha, group_id = lookup(D.user)
            # IPADDR = rem_addr (de onde o usuário conectou); sem ele, o IP do
            # equipamento — o mesmo fallback do RADIUS (Calling-Station-Id → NAS).
            # alguns NAS (ex.: Datacom DmOS) mandam rem_addr "0.0.0.0" / "::": não é IP real
            rem = (D.av_pairs.get(AV_A_IPADDR) or "").strip()
            if rem in ("0.0.0.0", "::", "0:0:0:0:0:0:0:0"):
                rem = ""
            origin = rem or D.av_pairs.get(AV_A_TACCLIENT)
            allowed = ip_allowed(group_id, origin)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"h2node_mavis: erro de banco: {exc}\n")
            sys.stderr.flush()
            D.write(MAVIS_FINAL, AV_V_RESULT_ERROR, "backend error")
            continue

        if pname is None:
            D.write(MAVIS_DOWN, AV_V_RESULT_NOTFOUND, None)
            continue
        if not ok_state:
            D.write(MAVIS_FINAL, AV_V_RESULT_FAIL, "conta desativada ou expirada")
            continue
        if not allowed:
            D.write(MAVIS_FINAL, AV_V_RESULT_FAIL, "IP de origem nao autorizado para o grupo")
            continue

        if D.is_tacplus_authc:
            if ssha and verify_ssha512(D.password, ssha):
                D.set_tacmember(f'"{pname}"')
                D.write(MAVIS_FINAL, AV_V_RESULT_OK, None)
            else:
                D.write(MAVIS_FINAL, AV_V_RESULT_FAIL, "autenticação falhou")
            continue

        if D.is_tacplus_authz:
            D.set_tacmember(f'"{pname}"')
            D.write(MAVIS_FINAL, AV_V_RESULT_OK, None)
            continue

        D.write(MAVIS_DOWN, AV_V_RESULT_NOTFOUND, None)


if __name__ == "__main__":
    main()
