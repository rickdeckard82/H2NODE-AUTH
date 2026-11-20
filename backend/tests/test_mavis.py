"""Regras do MAVIS (tacacs/h2node_mavis.py) — devem bater com as do RADIUS."""

import datetime
import importlib.util
import ipaddress
import sys
import types
from pathlib import Path

import pytest

_MAVIS = Path(__file__).resolve().parents[2] / "tacacs" / "h2node_mavis.py"
if not _MAVIS.is_file():  # a imagem do backend não leva o diretório tacacs/
    pytest.skip("tacacs/h2node_mavis.py fora da árvore", allow_module_level=True)


@pytest.fixture
def mavis(monkeypatch):
    # stubs da lib do tac_plus-ng e do password.py que o Dockerfile copia ao lado
    stub = types.ModuleType("mavis")
    for i, name in enumerate(
        ["AV_A_IPADDR", "AV_A_TACCLIENT", "AV_V_RESULT_ERROR", "AV_V_RESULT_FAIL",
         "AV_V_RESULT_NOTFOUND", "AV_V_RESULT_OK", "MAVIS_DOWN", "MAVIS_FINAL", "Mavis"]
    ):
        setattr(stub, name, i)
    pw = types.ModuleType("password")
    pw.verify_ssha512 = lambda *_: True
    monkeypatch.setitem(sys.modules, "mavis", stub)
    monkeypatch.setitem(sys.modules, "password", pw)
    spec = importlib.util.spec_from_file_location("h2node_mavis", _MAVIS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fake_db(users: dict, cidrs: dict):
    def query(sql: str, args: tuple = ()):
        if "FROM app_auth_user" in sql:
            return [users[args[0]]] if args[0] in users else []
        if "FROM radcheck" in sql:
            return [("{SSHA512}x",)]
        if "FROM app_auth_group_cidr" in sql:
            out = []
            for c in cidrs.get(args[0], []):
                net = ipaddress.ip_network(c)
                out.append((net.version, net.network_address.packed,
                            net.broadcast_address.packed))
            return out
        raise AssertionError(sql)
    return query


def test_lookup_state_and_ip_allowlist(mavis, monkeypatch):
    future = datetime.datetime(2999, 1, 1)
    past = datetime.datetime(2000, 1, 1)
    monkeypatch.setattr(mavis, "_query", _fake_db(
        users={
            "ok": (1, None, "admin-full", None),
            "off": (0, None, "admin-full", None),
            "old": (1, past, "admin-full", None),
            "grp": (1, future, "operator", 7),
        },
        cidrs={7: ["10.0.0.0/24", "2001:db8::/64"]},
    ))

    assert mavis.lookup("nobody")[1] is None
    assert mavis.lookup("ok")[0] is True
    assert mavis.lookup("off")[0] is False
    assert mavis.lookup("old")[0] is False

    gid = mavis.lookup("grp")[3]
    assert mavis.ip_allowed(None, "203.0.113.9")       # sem grupo: qualquer IP
    assert mavis.ip_allowed(gid, "10.0.0.200")
    assert mavis.ip_allowed(gid, "2001:db8::5")
    assert not mavis.ip_allowed(gid, "10.0.1.1")       # fora da faixa
    assert not mavis.ip_allowed(gid, "2001:db9::5")
    assert not mavis.ip_allowed(gid, None)              # sem IP => nega
    assert not mavis.ip_allowed(gid, "lixo")
