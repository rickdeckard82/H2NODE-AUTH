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


def _enable_mfa(auth_client) -> tuple[str, list[str]]:
    secret = auth_client.post("/api/auth/mfa/setup").json()["secret"]
    enable = auth_client.post("/api/auth/mfa/enable", json={"code": _current_totp(secret)})
    assert enable.status_code == 200, enable.text
    return secret, enable.json()["recovery_codes"]


def test_enable_returns_recovery_codes_and_me_counts_them(auth_client):
    _, codes = _enable_mfa(auth_client)
    assert len(codes) == 10
    assert len(set(codes)) == 10
    assert auth_client.get("/api/auth/me").json()["mfa_recovery_codes_remaining"] == 10


def test_recovery_code_logs_in_once_then_is_burned(auth_client):
    _, codes = _enable_mfa(auth_client)
    code = codes[0]

    body = auth_client.post(
        "/api/auth/login", json={"username": "admin", "password": "changeme-admin-123"}
    ).json()
    mfa_token = body["mfa_token"]

    verify = auth_client.post(
        "/api/auth/mfa/verify", json={"mfa_token": mfa_token, "code": code}
    )
    assert verify.status_code == 200, verify.text
    auth_client.headers.update({"X-CSRF-Token": verify.json()["csrf_token"]})
    assert auth_client.get("/api/auth/me").json()["mfa_recovery_codes_remaining"] == 9

    # o mesmo código não serve uma segunda vez
    body2 = auth_client.post(
        "/api/auth/login", json={"username": "admin", "password": "changeme-admin-123"}
    ).json()
    reuse = auth_client.post(
        "/api/auth/mfa/verify", json={"mfa_token": body2["mfa_token"], "code": code}
    )
    assert reuse.status_code == 401


def test_recovery_code_can_disable_mfa(auth_client):
    _, codes = _enable_mfa(auth_client)
    disable = auth_client.post(
        "/api/auth/mfa/disable",
        json={"password": "changeme-admin-123", "code": codes[-1]},
    )
    assert disable.status_code == 200, disable.text
    me = auth_client.get("/api/auth/me").json()
    assert me["mfa_enabled"] is False
    assert me["mfa_recovery_codes_remaining"] == 0


def test_regenerate_recovery_codes_invalidates_the_old_set(auth_client):
    secret, codes = _enable_mfa(auth_client)
    regen = auth_client.post(
        "/api/auth/mfa/recovery-codes/regenerate",
        json={"password": "changeme-admin-123", "code": _current_totp(secret)},
    )
    assert regen.status_code == 200, regen.text
    new_codes = regen.json()["recovery_codes"]
    assert set(new_codes).isdisjoint(codes)
    assert auth_client.get("/api/auth/me").json()["mfa_recovery_codes_remaining"] == 10

    body = auth_client.post(
        "/api/auth/login", json={"username": "admin", "password": "changeme-admin-123"}
    ).json()
    old = auth_client.post(
        "/api/auth/mfa/verify", json={"mfa_token": body["mfa_token"], "code": codes[0]}
    )
    assert old.status_code == 401


def test_regenerate_requires_valid_password_and_code(auth_client):
    secret, _ = _enable_mfa(auth_client)
    assert auth_client.post(
        "/api/auth/mfa/recovery-codes/regenerate",
        json={"password": "wrong", "code": _current_totp(secret)},
    ).status_code == 401
    assert auth_client.post(
        "/api/auth/mfa/recovery-codes/regenerate",
        json={"password": "changeme-admin-123", "code": "000000"},
    ).status_code == 401


def test_superadmin_can_reset_other_users_mfa(auth_client):
    r = auth_client.post("/api/system-users", json={
        "username": "mfa.user", "email": "mfa.user@example.com", "full_name": "MFA User",
        "role": "operator", "password": "changeme-123456",
    })
    uid = r.json()["id"]

    # não pode resetar quem não tem 2FA ativo
    assert auth_client.post(f"/api/system-users/{uid}/reset-mfa").status_code == 409


def _login_expecting_mfa(client) -> str:
    body = client.post(
        "/api/auth/login", json={"username": "admin", "password": "changeme-admin-123"}
    ).json()
    assert body["mfa_required"] is True
    return body["mfa_token"]


def test_remember_device_skips_mfa_on_next_login(auth_client):
    secret, _ = _enable_mfa(auth_client)

    mfa_token = _login_expecting_mfa(auth_client)
    verify = auth_client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": _current_totp(secret), "remember_device": True},
    )
    assert verify.status_code == 200, verify.text
    assert auth_client.cookies.get("pr_td")
    auth_client.headers.update({"X-CSRF-Token": verify.json()["csrf_token"]})

    # próximo login neste "navegador" não pede mais o código
    again = auth_client.post(
        "/api/auth/login", json={"username": "admin", "password": "changeme-admin-123"}
    )
    assert again.status_code == 200
    assert again.json()["mfa_required"] is False
    assert again.json()["user"]["username"] == "admin"


def test_without_remember_device_mfa_is_still_required(auth_client):
    secret, _ = _enable_mfa(auth_client)
    mfa_token = _login_expecting_mfa(auth_client)
    auth_client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": _current_totp(secret)},
    )
    assert not auth_client.cookies.get("pr_td")
    assert _login_expecting_mfa(auth_client)


def test_trusted_device_can_be_listed_and_revoked(auth_client):
    secret, _ = _enable_mfa(auth_client)
    mfa_token = _login_expecting_mfa(auth_client)
    verify = auth_client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": _current_totp(secret), "remember_device": True},
    )
    auth_client.headers.update({"X-CSRF-Token": verify.json()["csrf_token"]})

    devices = auth_client.get("/api/auth/mfa/trusted-devices").json()
    assert len(devices) == 1
    assert devices[0]["current"] is True

    assert auth_client.delete(
        f"/api/auth/mfa/trusted-devices/{devices[0]['id']}"
    ).status_code == 204
    assert auth_client.get("/api/auth/mfa/trusted-devices").json() == []
    # revogado => o 2FA volta a ser exigido
    assert _login_expecting_mfa(auth_client)


def test_trusted_device_history_in_audit(auth_client):
    secret, _ = _enable_mfa(auth_client)
    mfa_token = _login_expecting_mfa(auth_client)
    verify = auth_client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": _current_totp(secret), "remember_device": True},
    )
    auth_client.headers.update({"X-CSRF-Token": verify.json()["csrf_token"]})

    trail = auth_client.get(
        "/api/audit", params={"entity_type": "mfa_trusted_device"}
    ).json()["items"]
    assert [t["action"] for t in trail] == ["trust_device"]
    assert trail[0]["actor_username"] == "admin"

    dev_id = auth_client.get("/api/auth/mfa/trusted-devices").json()[0]["id"]
    assert auth_client.delete(f"/api/auth/mfa/trusted-devices/{dev_id}").status_code == 204

    actions = sorted(
        t["action"]
        for t in auth_client.get(
            "/api/audit", params={"entity_type": "mfa_trusted_device"}
        ).json()["items"]
    )
    assert actions == ["revoke_trusted_device", "trust_device"]

    # trocar a senha derruba os dispositivos e deixa rastro
    verify2 = auth_client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": _login_expecting_mfa(auth_client), "code": _current_totp(secret),
              "remember_device": True},
    )
    auth_client.headers.update({"X-CSRF-Token": verify2.json()["csrf_token"]})
    chg = auth_client.patch(
        "/api/auth/me/password",
        json={"current_password": "changeme-admin-123", "new_password": "another-new-secret-9"},
    )
    assert chg.status_code == 200, chg.text
    trail = auth_client.get(
        "/api/audit", params={"entity_type": "mfa_trusted_device", "action": "revoke_trusted_devices"}
    ).json()["items"]
    assert trail and trail[0]["before_json"] and "password_changed" in trail[0]["before_json"]


def test_disabling_mfa_drops_trusted_devices(auth_client):
    secret, _ = _enable_mfa(auth_client)
    mfa_token = _login_expecting_mfa(auth_client)
    verify = auth_client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": _current_totp(secret), "remember_device": True},
    )
    auth_client.headers.update({"X-CSRF-Token": verify.json()["csrf_token"]})

    auth_client.post(
        "/api/auth/mfa/disable",
        json={"password": "changeme-admin-123", "code": _current_totp(secret)},
    )
    # reativa o 2FA: não pode reaproveitar o dispositivo confiável antigo
    secret2, _ = _enable_mfa(auth_client)
    assert auth_client.get("/api/auth/mfa/trusted-devices").json() == []
    assert _login_expecting_mfa(auth_client)


def test_password_change_drops_trusted_devices(auth_client):
    secret, _ = _enable_mfa(auth_client)
    mfa_token = _login_expecting_mfa(auth_client)
    verify = auth_client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": _current_totp(secret), "remember_device": True},
    )
    auth_client.headers.update({"X-CSRF-Token": verify.json()["csrf_token"]})

    changed = auth_client.patch(
        "/api/auth/me/password",
        json={"current_password": "changeme-admin-123", "new_password": "brand-new-secret-1"},
    )
    assert changed.status_code == 200, changed.text
    assert auth_client.get("/api/auth/mfa/trusted-devices").json() == []
    body = auth_client.post(
        "/api/auth/login", json={"username": "admin", "password": "brand-new-secret-1"}
    ).json()
    assert body["mfa_required"] is True


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
