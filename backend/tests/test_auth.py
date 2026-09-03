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
