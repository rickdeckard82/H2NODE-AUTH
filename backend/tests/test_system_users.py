def test_me_exposes_timezone(auth_client):
    me = auth_client.get("/api/auth/me").json()
    assert me["timezone"] == "America/Sao_Paulo"


def test_create_and_update_system_user_timezone(auth_client):
    r = auth_client.post("/api/system-users", json={
        "username": "op.tz", "email": "op.tz@example.com", "full_name": "Op TZ",
        "role": "operator", "password": "changeme-123456", "timezone": "America/Manaus",
    })
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    assert r.json()["timezone"] == "America/Manaus"

    r = auth_client.patch(f"/api/system-users/{uid}", json={"timezone": "UTC"})
    assert r.status_code == 200
    assert r.json()["timezone"] == "UTC"


def test_reject_invalid_timezone(auth_client):
    r = auth_client.post("/api/system-users", json={
        "username": "op.bad", "email": "op.bad@example.com", "full_name": "Op Bad",
        "role": "operator", "password": "changeme-123456", "timezone": "Mars/Olympus",
    })
    assert r.status_code == 422

    r = auth_client.post("/api/system-users", json={
        "username": "op.ok", "email": "op.ok@example.com", "full_name": "Op OK",
        "role": "operator", "password": "changeme-123456",
    })
    assert r.status_code == 201
    assert r.json()["timezone"] == "America/Sao_Paulo"  # default


def test_language_default_and_set_on_create(auth_client):
    me = auth_client.get("/api/auth/me").json()
    assert me["language"] == "pt-BR"  # default

    r = auth_client.post("/api/system-users", json={
        "username": "op.lang", "email": "op.lang@example.com", "full_name": "Op Lang",
        "role": "operator", "password": "changeme-123456", "language": "en-US",
    })
    assert r.status_code == 201, r.text
    assert r.json()["language"] == "en-US"
    uid = r.json()["id"]

    r = auth_client.patch(f"/api/system-users/{uid}", json={"language": "pt-BR"})
    assert r.status_code == 200
    assert r.json()["language"] == "pt-BR"

    # valor inválido é rejeitado
    assert auth_client.post("/api/system-users", json={
        "username": "op.badlang", "email": "b@x.com", "full_name": "B",
        "role": "operator", "password": "changeme-123456", "language": "fr-FR",
    }).status_code == 422


def test_patch_me_language(auth_client):
    r = auth_client.patch("/api/auth/me", json={"language": "en-US"})
    assert r.status_code == 200, r.text
    assert r.json()["language"] == "en-US"
    assert auth_client.get("/api/auth/me").json()["language"] == "en-US"

    assert auth_client.patch("/api/auth/me", json={"language": "xx"}).status_code == 422
