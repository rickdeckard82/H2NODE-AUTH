def test_login_sets_cookies_and_me(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "changeme-admin-123"})
    assert r.status_code == 200
    assert "pr_access" in r.cookies
    assert "pr_refresh" in r.cookies
    body = r.json()
    assert body["user"]["role"] == "superadmin"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "admin"


def test_login_bad_password(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_protected_requires_auth(client):
    assert client.get("/api/system-users").status_code == 401


def test_csrf_required_for_writes(auth_client):
    auth_client.headers.pop("X-CSRF-Token", None)
    r = auth_client.post("/api/system-users", json={
        "username": "bob", "email": "bob@x.com", "full_name": "Bob",
        "role": "operator", "password": "supersecret1"})
    assert r.status_code == 403


def test_refresh_rotates(client):
    client.post("/api/auth/login", json={"username": "admin", "password": "changeme-admin-123"})
    first = client.cookies.get("pr_refresh")
    r = client.post("/api/auth/refresh")
    assert r.status_code == 200
    assert client.cookies.get("pr_refresh") != first


def test_login_lockout_after_failed_attempts(client):
    for _ in range(5):
        assert client.post(
            "/api/auth/login", json={"username": "admin", "password": "nope"}
        ).status_code == 401
    # bloqueada: mesmo com a senha correta agora retorna 429
    r = client.post("/api/auth/login", json={"username": "admin", "password": "changeme-admin-123"})
    assert r.status_code == 429


def test_login_unknown_user_is_401_not_429(client):
    for _ in range(6):
        r = client.post("/api/auth/login", json={"username": "ghost", "password": "whatever12345"})
        assert r.status_code == 401


def test_hsts_follows_cookie_secure(client):
    import app.main as main_module

    # testes rodam com COOKIE_SECURE=false (ver conftest) — sem HSTS
    r = client.get("/api/health")
    assert "strict-transport-security" not in {k.lower() for k in r.headers}

    main_module.settings.cookie_secure = True
    try:
        r = client.get("/api/health")
        assert r.headers["strict-transport-security"] == "max-age=63072000; includeSubDomains"
    finally:
        main_module.settings.cookie_secure = False


def test_password_change_ends_other_sessions(auth_client):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as other:  # outra sessão do mesmo usuário
        assert other.post("/api/auth/login", json={
            "username": "admin", "password": "changeme-admin-123"}).status_code == 200
        changed = auth_client.patch("/api/auth/me/password", json={
            "current_password": "changeme-admin-123", "new_password": "brand-new-secret-1"})
        assert changed.status_code == 200, changed.text
        # a sessão de quem trocou continua (recebeu um refresh novo)...
        assert auth_client.post("/api/auth/refresh").status_code == 200
        # ...a outra não (e reusar o token revogado derruba tudo, por projeto)
        assert other.post("/api/auth/refresh").status_code == 401


def test_concurrent_refresh_from_two_tabs_keeps_session(auth_client):
    old = auth_client.cookies.get("pr_refresh")
    assert auth_client.post("/api/auth/refresh").status_code == 200  # aba A
    # aba B chega com o cookie velho logo depois: conflito, não "roubo"
    r = auth_client.post("/api/auth/refresh", cookies={"pr_refresh": old})
    assert r.status_code == 409
    # a sessão nova (aba A) continua valendo
    assert auth_client.post("/api/auth/refresh").status_code == 200


def test_refresh_reuse_after_grace_still_revokes_everything(auth_client, seeded):
    from datetime import timedelta

    from app.core.security import utcnow
    from app.models import RefreshToken

    old = auth_client.cookies.get("pr_refresh")
    assert auth_client.post("/api/auth/refresh").status_code == 200
    for t in seeded.query(RefreshToken):  # simula o tempo passando além da janela
        t.issued_at = utcnow() - timedelta(minutes=5)
    seeded.commit()
    r = auth_client.post("/api/auth/refresh", cookies={"pr_refresh": old})
    assert r.status_code == 401
    assert seeded.query(RefreshToken).filter_by(revoked=False).count() == 0
