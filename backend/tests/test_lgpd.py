from datetime import datetime, timedelta

from sqlalchemy import select

from app.models import AuditLog, AuthUser, CmdAcct, LgpdSettings, PrivilegeProfile, RadPostAuth
from app.services import retention


def _operator(client, seeded):
    from app.core.security import hash_password
    from app.models import SystemRole, SystemUser
    seeded.add(SystemUser(username="op", email="op@x.com", full_name="Op",
                          role=SystemRole.operator, is_active=True,
                          password_hash=hash_password("operator-pass-1")))
    seeded.commit()
    login = client.post("/api/auth/login", json={"username": "op", "password": "operator-pass-1"})
    client.headers.update({"X-CSRF-Token": login.json()["csrf_token"]})
    return client


def test_lgpd_defaults_and_update(auth_client):
    cfg = auth_client.get("/api/settings/lgpd").json()
    assert cfg["accounting_retention_days"] == 0
    assert cfg["org_name"]  # padrão não vazio

    r = auth_client.put("/api/settings/lgpd", json={
        "org_name": "Empresa X LTDA", "dpo_email": "dpo@empresax.com",
        "accounting_retention_days": 365, "audit_retention_days": 730,
        "auth_user_retention_days": 90,
    })
    assert r.status_code == 200, r.text

    got = auth_client.get("/api/settings/lgpd").json()
    assert got["org_name"] == "Empresa X LTDA"
    assert got["accounting_retention_days"] == 365
    assert got["audit_retention_days"] == 730
    assert got["auth_user_retention_days"] == 90

    trail = auth_client.get("/api/audit", params={"entity_type": "lgpd_settings"}).json()["items"]
    assert trail and trail[0]["action"] in ("create", "update")


def test_legal_notice_is_public(client, auth_client):
    auth_client.put("/api/settings/lgpd", json={
        "org_name": "Pública SA", "dpo_email": "p@x.com",
        "accounting_retention_days": 30, "audit_retention_days": 60,
        "auth_user_retention_days": 0,
    })
    r = client.get("/api/settings/legal")
    assert r.status_code == 200
    body = r.json()
    assert body["org_name"] == "Pública SA"
    assert body["accounting_retention_days"] == 30
    assert "dpo_email" in body


def test_operator_cannot_touch_lgpd_but_sees_legal(client, seeded):
    op = _operator(client, seeded)
    assert op.get("/api/settings/lgpd").status_code == 403
    assert op.put("/api/settings/lgpd", json={
        "org_name": "x", "dpo_email": "x@x.com",
        "accounting_retention_days": 1, "audit_retention_days": 1, "auth_user_retention_days": 1,
    }).status_code == 403
    assert op.get("/api/settings/legal").status_code == 200


def test_retention_purge_deletes_old_data(seeded, monkeypatch):
    monkeypatch.setattr(retention, "_BATCH", 1)  # força vários lotes
    now = datetime.now()
    old = now - timedelta(days=400)
    recent = now - timedelta(days=5)
    pid = seeded.execute(select(PrivilegeProfile.id)).scalars().first()

    seeded.add_all([
        RadPostAuth(username="a", pass_="", reply="Access-Accept", authdate=old),
        RadPostAuth(username="a2", pass_="", reply="Access-Reject", authdate=old),
        RadPostAuth(username="b", pass_="", reply="Access-Accept", authdate=recent),
        CmdAcct(event_time=old, nasipaddress="10.0.0.1", username="a",
                callingstationid="", action="exec", command="show", acctsessionid="s1"),
        CmdAcct(event_time=recent, nasipaddress="10.0.0.1", username="b",
                callingstationid="", action="exec", command="show", acctsessionid="s2"),
        AuditLog(action="login", entity_type="system_user", created_at=old),
        AuditLog(action="login", entity_type="system_user", created_at=recent),
        AuthUser(username="stale.disabled", privilege_profile_id=pid,
                 is_active=False, last_auth_at=old),
        AuthUser(username="stale.active", privilege_profile_id=pid,
                 is_active=True, last_auth_at=old),
        AuthUser(username="fresh.disabled", privilege_profile_id=pid,
                 is_active=False, last_auth_at=recent),
        LgpdSettings(org_name="X", dpo_email="x@x.com",
                     accounting_retention_days=365, audit_retention_days=365,
                     auth_user_retention_days=90),
    ])
    seeded.commit()

    counts = retention.run_if_due(seeded)
    assert counts == {"radpostauth": 2, "cmd_acct": 1, "audit_log": 1, "auth_user": 1}

    assert [r.username for r in seeded.execute(select(RadPostAuth)).scalars()] == ["b"]
    assert {u.username for u in seeded.execute(select(AuthUser)).scalars()} == {
        "stale.active", "fresh.disabled"
    }

    cfg = seeded.execute(select(LgpdSettings)).scalars().one()
    assert cfg.last_purge_at is not None
    # segunda chamada imediata é no-op (dentro da janela de 24h)
    assert retention.run_if_due(seeded) is None


def test_retention_noop_when_all_zero(seeded):
    seeded.add_all([
        LgpdSettings(org_name="X", dpo_email="x@x.com"),
        RadPostAuth(username="a", pass_="", reply="Access-Accept",
                    authdate=datetime.now() - timedelta(days=9999)),
    ])
    seeded.commit()
    assert retention.run_if_due(seeded) is None
    assert seeded.execute(select(RadPostAuth)).scalars().first() is not None
