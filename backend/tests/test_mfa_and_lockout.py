import pyotp
import pytest

from app.core.ratelimit import limiter


def test_progressive_lockout_grows_on_repeat_offense(client, seeded):
    from app.models import SystemUser

    def _fail_five_times():
        for _ in range(5):
            assert client.post(
                "/api/auth/login", json={"username": "admin", "password": "nope"}
            ).status_code == 401

    _fail_five_times()
    user = seeded.query(SystemUser).filter_by(username="admin").one()
    assert user.lockout_strikes == 1
    first_duration = user.locked_until

    # força o desbloqueio (simula o tempo passando) e repete a ofensa
    user.locked_until = None
    user.failed_login_count = 0
    seeded.commit()

    _fail_five_times()
    seeded.refresh(user)
    assert user.lockout_strikes == 2
    # segundo bloqueio deve ser mais longo que o primeiro (backoff exponencial)
    assert user.locked_until > first_duration


def test_successful_login_resets_lockout_strikes(client, seeded):
    from app.models import SystemUser

    for _ in range(5):
        client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    user = seeded.query(SystemUser).filter_by(username="admin").one()
    assert user.lockout_strikes == 1

    user.locked_until = None
    seeded.commit()

    ok = client.post("/api/auth/login", json={"username": "admin", "password": "changeme-admin-123"})
    assert ok.status_code == 200
    seeded.refresh(user)
    assert user.lockout_strikes == 0
    assert user.failed_login_count == 0


def _current_totp(secret: str) -> str:
    return pyotp.TOTP(secret).now()


def test_mfa_setup_enable_login_and_disable(auth_client):
    # login normal ainda funciona sem 2FA configurado
    me = auth_client.get("/api/auth/me").json()
    assert me["mfa_enabled"] is False

    setup = auth_client.post("/api/auth/mfa/setup")
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    assert "otpauth://totp/" in setup.json()["otpauth_uri"]

    bad_enable = auth_client.post("/api/auth/mfa/enable", json={"code": "000000"})
    assert bad_enable.status_code == 401

    enable = auth_client.post("/api/auth/mfa/enable", json={"code": _current_totp(secret)})
    assert enable.status_code == 200, enable.text
    assert auth_client.get("/api/auth/me").json()["mfa_enabled"] is True

    # novo login agora exige 2ª etapa
    login = auth_client.post(
        "/api/auth/login", json={"username": "admin", "password": "changeme-admin-123"}
    )
    assert login.status_code == 200
    body = login.json()
    assert body["mfa_required"] is True
    assert body["user"] is None
    mfa_token = body["mfa_token"]

    bad_verify = auth_client.post("/api/auth/mfa/verify", json={"mfa_token": mfa_token, "code": "000000"})
    assert bad_verify.status_code == 401

    verify = auth_client.post(
        "/api/auth/mfa/verify", json={"mfa_token": mfa_token, "code": _current_totp(secret)}
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["user"]["username"] == "admin"
    # mfa/verify emite uma sessão nova — atualiza o CSRF que o client usa
    auth_client.headers.update({"X-CSRF-Token": verify.json()["csrf_token"]})

    # desativar exige senha + código válido
    bad_disable = auth_client.post(
        "/api/auth/mfa/disable", json={"password": "wrong", "code": _current_totp(secret)}
    )
    assert bad_disable.status_code == 401

    disable = auth_client.post(
        "/api/auth/mfa/disable",
        json={"password": "changeme-admin-123", "code": _current_totp(secret)},
    )
    assert disable.status_code == 200, disable.text
    assert auth_client.get("/api/auth/me").json()["mfa_enabled"] is False


def test_superadmin_can_reset_other_users_mfa(auth_client):
    r = auth_client.post("/api/system-users", json={
        "username": "mfa.user", "email": "mfa.user@example.com", "full_name": "MFA User",
        "role": "operator", "password": "changeme-123456",
    })
    uid = r.json()["id"]

    # não pode resetar quem não tem 2FA ativo
    assert auth_client.post(f"/api/system-users/{uid}/reset-mfa").status_code == 409


def test_invite_accept_is_rate_limited(client):
    limiter.enabled = True
    try:
        statuses = [
            client.post("/api/auth/invite/accept", json={
                "token": "not-a-real-token", "password": "whatever-1234",
            }).status_code
            for _ in range(11)
        ]
    finally:
        limiter.enabled = False
    assert statuses[:10] == [404] * 10
    assert statuses[10] == 429


@pytest.fixture(autouse=True)
def _keep_limiter_disabled():
    yield
    limiter.enabled = False
