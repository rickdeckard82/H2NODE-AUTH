import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import mailer
from tests.conftest import first_manufacturer_id


@pytest.fixture
def sent_emails(monkeypatch):
    """Substitui o envio real por um registro em memória."""
    calls: list[dict] = []

    def _fake_send(db, *, to, subject, html, text):
        calls.append({"to": to, "subject": subject, "html": html, "text": text})

    monkeypatch.setattr(mailer, "send_mail", _fake_send)
    return calls


def _configure_smtp(auth_client) -> None:
    r = auth_client.put("/api/settings/smtp", json={
        "host": "smtp.example.com", "port": 587, "username": "bot@example.com",
        "password": "s3cr3t-smtp-pass", "use_tls": True, "use_ssl": False,
        "from_email": "no-reply@example.com", "from_name": "H2NODE Auth",
    })
    assert r.status_code == 200, r.text


def test_smtp_settings_roundtrip(auth_client):
    assert auth_client.get("/api/settings/smtp").json() is None
    _configure_smtp(auth_client)
    out = auth_client.get("/api/settings/smtp").json()
    assert out["host"] == "smtp.example.com"
    assert out["has_password"] is True
    assert "password" not in out


def test_create_user_without_password_requires_smtp(auth_client):
    r = auth_client.post("/api/system-users", json={
        "username": "pending.user", "email": "pending@example.com", "full_name": "Pending User",
        "role": "operator",
    })
    assert r.status_code == 422, r.text


def test_invite_flow(auth_client, sent_emails):
    _configure_smtp(auth_client)

    r = auth_client.post("/api/system-users", json={
        "username": "invitee", "email": "invitee@example.com", "full_name": "Invitee",
        "role": "operator",
    })
    assert r.status_code == 201, r.text
    assert r.json()["has_password"] is False
    uid = r.json()["id"]

    assert len(sent_emails) == 1
    link = sent_emails[0]["text"]
    token = link.split("token=")[1].split("\n")[0].strip()

    # convite válido
    info = auth_client.get(f"/api/auth/invite/{token}")
    assert info.status_code == 200, info.text
    assert info.json()["username"] == "invitee"

    # aceitar convite loga o usuário (em uma sessão própria) e define a senha
    with TestClient(app) as invitee_client:
        accept = invitee_client.post("/api/auth/invite/accept", json={
            "token": token, "password": "invitee-new-pass-1",
        })
        assert accept.status_code == 200, accept.text
        assert accept.json()["user"]["username"] == "invitee"

        # convite já usado não pode ser reaproveitado
        reuse = invitee_client.post("/api/auth/invite/accept", json={
            "token": token, "password": "another-password-1",
        })
        assert reuse.status_code == 404

    users = auth_client.get("/api/system-users").json()["items"]
    invited = next(u for u in users if u["id"] == uid)
    assert invited["has_password"] is True

    # não é possível reenviar convite para quem já tem senha
    resend = auth_client.post(f"/api/system-users/{uid}/resend-invite")
    assert resend.status_code == 409


def test_resend_invite(auth_client, sent_emails):
    _configure_smtp(auth_client)
    r = auth_client.post("/api/system-users", json={
        "username": "resend.me", "email": "resend@example.com", "full_name": "Resend Me",
        "role": "operator",
    })
    uid = r.json()["id"]
    assert len(sent_emails) == 1

    r = auth_client.post(f"/api/system-users/{uid}/resend-invite")
    assert r.status_code == 200, r.text
    assert len(sent_emails) == 2

    old_token = sent_emails[0]["text"].split("token=")[1].split("\n")[0].strip()
    new_token = sent_emails[1]["text"].split("token=")[1].split("\n")[0].strip()
    assert old_token != new_token

    # o convite antigo foi invalidado pelo reenvio
    assert auth_client.get(f"/api/auth/invite/{old_token}").status_code == 404
    assert auth_client.get(f"/api/auth/invite/{new_token}").status_code == 200


def test_change_own_password(auth_client):
    ok = auth_client.patch("/api/auth/me/password", json={
        "current_password": "changeme-admin-123", "new_password": "brand-new-password-1",
    })
    assert ok.status_code == 200, ok.text
    # a troca emite sessão nova (as outras caem); o front lê o CSRF do cookie
    auth_client.headers.update({"X-CSRF-Token": auth_client.cookies.get("pr_csrf")})

    bad = auth_client.patch("/api/auth/me/password", json={
        "current_password": "wrong-password", "new_password": "another-password-1",
    })
    assert bad.status_code == 401


def test_reveal_manufacturer_secret(auth_client, seeded):
    mid = first_manufacturer_id(seeded)
    auth_client.patch(f"/api/manufacturers/{mid}", json={
        "radius_secret": "mfr-plain-secret", "tacacs_key": "mfr-tac-key-9",
    })
    r = auth_client.get(f"/api/manufacturers/{mid}/secret")
    assert r.status_code == 200, r.text
    assert r.json()["radius_secret"] == "mfr-plain-secret"
    assert r.json()["tacacs_key"] == "mfr-tac-key-9"


def test_reveal_equipment_secret_own_and_inherited(auth_client, seeded):
    mid = first_manufacturer_id(seeded)
    own = auth_client.post("/api/equipment", json={
        "name": "core-01", "mgmt_ip": "10.10.0.1", "manufacturer_id": mid,
        "shortname": "core-01", "radius_secret": "own-secret-value",
    }).json()
    r = auth_client.get(f"/api/equipment/{own['id']}/secret")
    assert r.status_code == 200, r.text
    assert r.json() == {"radius_secret": "own-secret-value", "source": "equipment"}

    auth_client.patch(f"/api/manufacturers/{mid}", json={"radius_secret": "mfr-inherited-secret"})
    inherited = auth_client.post("/api/equipment", json={
        "name": "core-02", "mgmt_ip": "10.10.0.2", "manufacturer_id": mid, "shortname": "core-02",
    }).json()
    r = auth_client.get(f"/api/equipment/{inherited['id']}/secret")
    assert r.status_code == 200, r.text
    assert r.json() == {"radius_secret": "mfr-inherited-secret", "source": "manufacturer"}
