from datetime import datetime, timedelta

from app.models import CmdAcct, RadPostAuth


def _seed_authn(db):
    now = datetime(2026, 9, 3, 18, 0, 0)
    db.add_all([
        RadPostAuth(username="everton", pass_="", reply="Access-Accept", authdate=now),
        RadPostAuth(username="everton", pass_="", reply="Access-Reject",
                    authdate=now - timedelta(hours=1)),
        RadPostAuth(username="joao", pass_="", reply="Access-Accept",
                    authdate=now - timedelta(days=2)),
    ])
    db.commit()


def _seed_cmds(db):
    now = datetime(2026, 9, 3, 18, 0, 0)
    db.add_all([
        CmdAcct(event_time=now, nasipaddress="10.0.0.9", username="everton",
                callingstationid="192.0.2.5", action="exec",
                command="show running-config", acctsessionid="s1"),
        CmdAcct(event_time=now - timedelta(hours=2), nasipaddress="10.0.0.10",
                username="joao", callingstationid="192.0.2.6", action="config",
                # como o rlm_sql grava: chars fora de safe_characters viram =XX
                command="snmp-server community =27public=27 =3B show ip route",
                acctsessionid="s2"),
    ])
    db.commit()


def test_authentication_list_and_filter(auth_client, seeded):
    _seed_authn(seeded)
    r = auth_client.get("/api/accounting/authentication")
    assert r.status_code == 200
    assert r.json()["total"] == 3

    r = auth_client.get("/api/accounting/authentication", params={"accepted": "false"})
    assert [i["username"] for i in r.json()["items"]] == ["everton"]

    r = auth_client.get("/api/accounting/authentication", params={"username": "joa"})
    assert r.json()["total"] == 1
    # data serializada com offset UTC explícito
    assert r.json()["items"][0]["authdate"].endswith("+00:00")


def test_authentication_alias_still_works(auth_client, seeded):
    _seed_authn(seeded)
    assert auth_client.get("/api/accounting/auth-events").json()["total"] == 3


def test_authentication_csv(auth_client, seeded):
    _seed_authn(seeded)
    r = auth_client.get("/api/accounting/authentication.csv")
    assert r.status_code == 200
    assert "authdate_utc,username,reply" in r.text
    assert "Access-Reject" in r.text


def test_commands_list_filter_and_unescape(auth_client, seeded):
    _seed_cmds(seeded)
    r = auth_client.get("/api/accounting/commands")
    assert r.status_code == 200
    items = r.json()["items"]
    assert items[0]["command"] == "show running-config"
    # a rota reverte o escape =XX do rlm_sql
    assert items[1]["command"] == "snmp-server community 'public' ; show ip route"
    assert items[0]["event_time"].endswith("+00:00")

    r = auth_client.get("/api/accounting/commands", params={"nas_ip": "10.0.0.10"})
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["username"] == "joao"

    r = auth_client.get("/api/accounting/commands", params={"action": "exec"})
    assert r.json()["total"] == 1


def test_commands_csv_unescaped(auth_client, seeded):
    _seed_cmds(seeded)
    r = auth_client.get("/api/accounting/commands.csv")
    assert "snmp-server community 'public' ; show ip route" in r.text


def test_reports_require_auth(client):
    assert client.get("/api/accounting/commands").status_code == 401
