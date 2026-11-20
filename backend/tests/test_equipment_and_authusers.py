from app.models import Nas, RadCheck, RadGroupReply, RadUserGroup
from app.services.password import make_nt_hash, verify_ssha512
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


def test_require_message_authenticator_exception_propagates_to_nas(auth_client, seeded):
    mid = first_manufacturer_id(seeded)
    r = auth_client.post("/api/equipment", json={
        "name": "mk-legacy", "mgmt_ip": "10.0.0.9", "manufacturer_id": mid,
        "shortname": "mk-legacy", "radius_secret": "s3cr3t-shared",
        "radius_require_message_authenticator": False,
    })
    assert r.status_code == 201, r.text
    assert r.json()["radius_require_message_authenticator"] is False
    nas = seeded.query(Nas).filter_by(nasname="10.0.0.9").one()
    assert nas.require_message_authenticator is False

    eq_id = r.json()["id"]
    up = auth_client.patch(f"/api/equipment/{eq_id}", json={
        "radius_require_message_authenticator": True,
    })
    assert up.status_code == 200, up.text
    assert up.json()["radius_require_message_authenticator"] is True
    seeded.refresh(nas)
    assert nas.require_message_authenticator is True


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

    chk = seeded.query(RadCheck).filter_by(
        username="noc.jdoe", attribute="SSHA2-512-Password").one()
    assert verify_ssha512("Str0ngPass!x12", chk.value)
    nt = seeded.query(RadCheck).filter_by(
        username="noc.jdoe", attribute="NT-Password").one()
    assert nt.value == make_nt_hash("Str0ngPass!x12")

    grp = seeded.query(RadUserGroup).filter_by(username="noc.jdoe").one()
    assert grp.groupname.startswith("profile_")
    assert seeded.query(RadGroupReply).filter_by(groupname=grp.groupname).count() >= 1


def test_a10_manufacturer_seeded_with_privilege_attr(auth_client, seeded):
    from app.models import Manufacturer

    m = seeded.query(Manufacturer).filter_by(name="a10").one()
    assert m.vendor_kind.value == "a10"
    assert m.radius_vendor_id == 22610

    # os perfis embutidos carregam o VSA do A10 no radgroupreply
    rows = seeded.query(RadGroupReply).filter_by(attribute="A10-Admin-Privilege").all()
    assert {r.value for r in rows} == {"3", "12", "14"}


def test_zte_manufacturer_seeded(auth_client, seeded):
    from app.models import Manufacturer

    m = seeded.query(Manufacturer).filter_by(name="zte").one()
    assert m.vendor_kind.value == "zte"
    assert m.radius_vendor_id == 3902

    # ZTE hoje só fala TACACS+: sem VSA próprio, nenhum atributo de perfil é criado
    rows = seeded.query(RadGroupReply).filter(
        RadGroupReply.groupname.like("%"), RadGroupReply.attribute.like("ZTE%")
    ).all()
    assert rows == []


def test_dell_manufacturer_seeded(auth_client, seeded):
    from app.models import Manufacturer

    m = seeded.query(Manufacturer).filter_by(name="dell").one()
    assert m.vendor_kind.value == "dell"
    assert m.radius_vendor_id == 674

    # Dell hoje só fala TACACS+: sem VSA próprio, nenhum atributo de perfil é criado
    rows = seeded.query(RadGroupReply).filter(
        RadGroupReply.groupname.like("%"), RadGroupReply.attribute.like("Dell%")
    ).all()
    assert rows == []


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


def _operator_client(client, seeded):
    from app.core.security import hash_password
    from app.models import SystemRole, SystemUser
    seeded.add(SystemUser(username="op", email="op@x.com", full_name="Op",
                          role=SystemRole.operator, is_active=True,
                          password_hash=hash_password("operator-pass-1")))
    seeded.commit()
    login = client.post("/api/auth/login", json={"username": "op", "password": "operator-pass-1"})
    client.headers.update({"X-CSRF-Token": login.json()["csrf_token"]})
    return client


def test_operator_cannot_manage_system_users(client, seeded):
    op = _operator_client(client, seeded)
    assert op.get("/api/system-users").status_code == 403


def test_operator_permission_boundaries(auth_client, client, seeded):
    # o admin cria os recursos que o operador vai tentar mexer
    mid = first_manufacturer_id(seeded)
    eq_id = auth_client.post("/api/equipment", json={
        "name": "op-eq", "mgmt_ip": "10.9.9.9", "manufacturer_id": mid,
        "shortname": "op-eq", "radius_secret": "s3cr3t-op-123",
    }).json()["id"]
    profile_id = auth_client.get("/api/privilege-profiles").json()[0]["id"]
    au_id = auth_client.post("/api/auth-users", json={
        "username": "op.victim", "privilege_profile_id": profile_id, "password": "Str0ngPass!x12",
    }).json()["id"]
    grp_id = auth_client.post("/api/auth-groups", json={"name": "op-grp"}).json()["id"]

    op = _operator_client(client, seeded)

    # não vê a auditoria (nem o histórico de dispositivos 2FA)
    assert op.get("/api/audit").status_code == 403
    assert op.get("/api/audit/trusted-devices").status_code == 403
    # não exclui equipamento nem usuário de autenticação
    assert op.delete(f"/api/equipment/{eq_id}").status_code == 403
    assert op.delete(f"/api/auth-users/{au_id}").status_code == 403
    # não cria/edita/exclui grupo de usuário
    assert op.post("/api/auth-groups", json={"name": "nope"}).status_code == 403
    assert op.patch(f"/api/auth-groups/{grp_id}", json={"description": "x"}).status_code == 403
    assert op.delete(f"/api/auth-groups/{grp_id}").status_code == 403

    # ainda pode: ler grupos (p/ atribuir a usuários), criar usuário, editar equipamento
    assert op.get("/api/auth-groups").status_code == 200
    assert op.patch(f"/api/equipment/{eq_id}", json={"site": "lab"}).status_code == 200
    assert op.post("/api/auth-users", json={
        "username": "op.created", "privilege_profile_id": profile_id, "password": "Str0ngPass!x12",
    }).status_code == 201


def test_auditor_cannot_see_audit_or_users(client, seeded):
    from app.core.security import hash_password
    from app.models import SystemRole, SystemUser
    seeded.add(SystemUser(username="aud", email="aud@x.com", full_name="Aud",
                          role=SystemRole.auditor, is_active=True,
                          password_hash=hash_password("auditor-pass-1")))
    seeded.commit()
    login = client.post("/api/auth/login", json={"username": "aud", "password": "auditor-pass-1"})
    client.headers.update({"X-CSRF-Token": login.json()["csrf_token"]})
    # sem acesso a auditoria nem à área de usuários
    assert client.get("/api/audit").status_code == 403
    assert client.get("/api/audit/trusted-devices").status_code == 403
    assert client.get("/api/auth-users").status_code == 403
    assert client.get("/api/auth-groups").status_code == 403
    assert client.get("/api/privilege-profiles").status_code == 403
    # mas segue com a leitura de equipamentos e dos relatórios AAA
    assert client.get("/api/equipment").status_code == 200
    assert client.get("/api/accounting/authentication").status_code == 200


def test_auth_user_expiry_is_utc_and_can_be_cleared(auth_client):
    profile_id = auth_client.get("/api/privilege-profiles").json()[0]["id"]
    r = auth_client.post("/api/auth-users", json={
        "username": "temp.user", "privilege_profile_id": profile_id,
        "password": "Str0ngPass!x12", "expires_at": "2030-01-01T23:59:00-03:00",
    })
    assert r.status_code == 201, r.text
    # guardado em UTC e devolvido com o fuso explícito
    assert r.json()["expires_at"] == "2030-01-02T02:59:00+00:00"
    uid = r.json()["id"]

    # PATCH sem o campo não mexe; com null remove
    assert auth_client.patch(f"/api/auth-users/{uid}", json={"full_name": "T"}).json()[
        "expires_at"] == "2030-01-02T02:59:00+00:00"
    assert auth_client.patch(f"/api/auth-users/{uid}", json={"expires_at": None}).json()[
        "expires_at"] is None
