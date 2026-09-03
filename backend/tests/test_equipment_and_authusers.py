from app.models import Nas, RadCheck, RadGroupReply, RadUserGroup
from app.services.password import verify_ssha512
from tests.conftest import first_manufacturer_id


def test_create_equipment_creates_nas(auth_client, seeded):
    mid = first_manufacturer_id(seeded)
    r = auth_client.post("/api/equipment", json={
        "name": "core-sw-01", "mgmt_ip": "10.0.0.1", "manufacturer_id": mid,
        "shortname": "core-sw-01", "radius_secret": "s3cr3t-shared",
    })
    assert r.status_code == 201, r.text
    assert r.json()["secret_source"] == "equipment"
    nas = seeded.query(Nas).filter_by(nasname="10.0.0.1").one()
    assert nas.secret == "s3cr3t-shared"
    assert nas.type == "huawei"


def test_equipment_inherits_manufacturer_secret(auth_client, seeded):
    mid = first_manufacturer_id(seeded)
    # define o segredo padrão no fabricante
    up = auth_client.patch(f"/api/manufacturers/{mid}", json={"radius_secret": "mfr-default-secret"})
    assert up.status_code == 200, up.text
    assert up.json()["has_secret"] is True

    # equipamento SEM segredo próprio -> herda
    r = auth_client.post("/api/equipment", json={
        "name": "olt-01", "mgmt_ip": "10.0.0.2", "manufacturer_id": mid, "shortname": "olt-01",
    })
    assert r.status_code == 201, r.text
    assert r.json()["secret_source"] == "manufacturer"
    assert r.json()["has_own_secret"] is False
    assert seeded.query(Nas).filter_by(nasname="10.0.0.2").one().secret == "mfr-default-secret"

    # trocar o segredo do fabricante re-propaga para quem herda
    auth_client.patch(f"/api/manufacturers/{mid}", json={"radius_secret": "rotated-secret"})
    assert seeded.query(Nas).filter_by(nasname="10.0.0.2").one().secret == "rotated-secret"


def test_equipment_without_secret_and_without_manufacturer_secret_fails(auth_client, seeded):
    mid = first_manufacturer_id(seeded)
    r = auth_client.post("/api/equipment", json={
        "name": "x", "mgmt_ip": "10.0.0.9", "manufacturer_id": mid, "shortname": "x",
    })
    assert r.status_code == 422


def test_manufacturer_crud_and_delete_guard(auth_client, seeded):
    r = auth_client.post("/api/manufacturers", json={
        "name": "nokia", "display_name": "Nokia", "vendor_kind": "generic",
        "radius_secret": "nokia-secret",
    })
    assert r.status_code == 201, r.text
    nid = r.json()["id"]

    eq = auth_client.post("/api/equipment", json={
        "name": "n1", "mgmt_ip": "10.0.1.1", "manufacturer_id": nid, "shortname": "n1",
    })
    assert eq.status_code == 201
    # não pode remover fabricante em uso
    assert auth_client.delete(f"/api/manufacturers/{nid}").status_code == 409


def test_create_auth_user_writes_radcheck_and_group(auth_client, seeded):
    profile_id = auth_client.get("/api/privilege-profiles").json()[0]["id"]
    r = auth_client.post("/api/auth-users", json={
        "username": "noc.jdoe", "privilege_profile_id": profile_id,
        "password": "Str0ngPass!x12",
    })
    assert r.status_code == 201, r.text

    chk = seeded.query(RadCheck).filter_by(username="noc.jdoe").one()
    assert chk.attribute == "SSHA2-512-Password"
    assert verify_ssha512("Str0ngPass!x12", chk.value)

    grp = seeded.query(RadUserGroup).filter_by(username="noc.jdoe").one()
    assert grp.groupname.startswith("profile_")
    assert seeded.query(RadGroupReply).filter_by(groupname=grp.groupname).count() >= 1


def test_auth_group_crud_and_user_assignment(auth_client, seeded):
    from app.models import AuthGroupCidr

    r = auth_client.post("/api/auth-groups", json={
        "name": "noc-lan", "description": "só da LAN do NOC",
        "cidrs": [{"cidr": "10.0.0.0/24", "note": "core"}, {"cidr": "192.168.1.5"}],
    })
    assert r.status_code == 201, r.text
    gid = r.json()["id"]
    assert {c["cidr"] for c in r.json()["cidrs"]} == {"10.0.0.0/24", "192.168.1.5/32"}

    starts = {c.ip_start for c in seeded.query(AuthGroupCidr).filter_by(group_id=gid)}
    assert bytes([10, 0, 0, 0]) in starts  # limite compatível com INET6_ATON

    profile_id = auth_client.get("/api/privilege-profiles").json()[0]["id"]
    u = auth_client.post("/api/auth-users", json={
        "username": "noc.ip", "privilege_profile_id": profile_id,
        "auth_group_id": gid, "password": "LongPass12345",
    })
    assert u.status_code == 201, u.text
    assert u.json()["auth_group_name"] == "noc-lan"

    # não pode remover grupo com membros
    assert auth_client.delete(f"/api/auth-groups/{gid}").status_code == 409

    # desvincular (auth_group_id=0) e então remover
    uid = u.json()["id"]
    detached = auth_client.patch(f"/api/auth-users/{uid}", json={"auth_group_id": 0})
    assert detached.json()["auth_group_name"] is None
    assert auth_client.delete(f"/api/auth-groups/{gid}").status_code == 204


def test_auth_group_rejects_bad_cidr(auth_client, seeded):
    r = auth_client.post("/api/auth-groups", json={
        "name": "bad", "cidrs": [{"cidr": "não-é-ip"}]})
    assert r.status_code == 422


def test_disable_auth_user_keeps_row_but_flags_inactive(auth_client, seeded):
    profile_id = auth_client.get("/api/privilege-profiles").json()[0]["id"]
    created = auth_client.post("/api/auth-users", json={
        "username": "temp.user", "privilege_profile_id": profile_id, "password": "Str0ngPass!x12",
    }).json()
    r = auth_client.patch(f"/api/auth-users/{created['id']}", json={"is_active": False})
    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_operator_cannot_manage_system_users(client, seeded):
    from app.core.security import hash_password
    from app.models import SystemRole, SystemUser
    seeded.add(SystemUser(username="op", email="op@x.com", full_name="Op",
                          role=SystemRole.operator, is_active=True,
                          password_hash=hash_password("operator-pass-1")))
    seeded.commit()
    login = client.post("/api/auth/login", json={"username": "op", "password": "operator-pass-1"})
    client.headers.update({"X-CSRF-Token": login.json()["csrf_token"]})
    assert client.get("/api/system-users").status_code == 403
