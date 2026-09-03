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
