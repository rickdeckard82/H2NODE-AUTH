import pytest

from app.core.crypto import encrypt
from app.models import Equipment, Manufacturer, Nas
from app.models.manufacturer import AaaProtocol, VendorKind
from app.services import radius_sync, tacacs_sync


@pytest.fixture
def mfr(db):
    m = Manufacturer(
        name="juniper-t", display_name="Juniper T", vendor_kind=VendorKind.juniper,
        aaa_protocol=AaaProtocol.tacacs, tacacs_key_enc=encrypt("grp-key-123"),
    )
    db.add(m)
    db.flush()
    return m


def _eq(db, mfr, **kw):
    e = Equipment(
        name=kw.get("name", "sw1"), mgmt_ip=kw.get("mgmt_ip", "10.9.9.9"),
        manufacturer_id=mfr.id, shortname=kw.get("shortname", "sw1"),
        aaa_protocol=kw.get("aaa_protocol"), tacacs_key_enc=kw.get("tacacs_key_enc"),
        radius_secret_enc=kw.get("radius_secret_enc"),
    )
    db.add(e)
    db.flush()
    return e


def test_resolve_protocol_and_key_inheritance(db, mfr):
    e = _eq(db, mfr)
    assert tacacs_sync.resolve_protocol(e, mfr) == AaaProtocol.tacacs
    assert tacacs_sync.resolve_tacacs_key(e, mfr) == "grp-key-123"

    e.tacacs_key_enc = encrypt("own-key-999")
    assert tacacs_sync.resolve_tacacs_key(e, mfr) == "own-key-999"

    e.aaa_protocol = AaaProtocol.radius
    assert tacacs_sync.resolve_protocol(e, mfr) == AaaProtocol.radius


def test_build_config_has_host_and_ruleset(db, seeded, mfr):
    _eq(db, mfr, mgmt_ip="192.0.2.1", name="core", shortname="core")
    text, n = tacacs_sync.build_config(db)
    assert n == 1
    assert "host eq_" in text
    assert "address = 192.0.2.1" in text
    assert 'key = "grp-key-123"' in text
    # perfis internos viram profile + regra no ruleset
    assert "profile admin-full {" in text
    assert 'if (member == "admin-full")' in text
    assert "set priv-lvl = 15" in text
    assert "enable 15 = login" in text


def test_tacacs_equipment_not_in_nas(db, mfr):
    e = _eq(db, mfr, mgmt_ip="10.1.1.1")
    radius_sync.sync_equipment(db, e, manufacturer=mfr)
    assert db.query(Nas).filter_by(nasname="10.1.1.1").first() is None


def test_switch_radius_to_tacacs_removes_nas(db):
    m = Manufacturer(
        name="dm", display_name="DM", vendor_kind=VendorKind.datacom,
        aaa_protocol=AaaProtocol.radius, radius_secret_enc=encrypt("rad-secret"),
        tacacs_key_enc=encrypt("tac-key"),
    )
    db.add(m)
    db.flush()
    e = _eq(db, m, mgmt_ip="10.2.2.2", aaa_protocol=AaaProtocol.radius)
    radius_sync.sync_equipment(db, e, manufacturer=m)
    db.flush()
    assert db.query(Nas).filter_by(nasname="10.2.2.2").first() is not None

    e.aaa_protocol = AaaProtocol.tacacs
    radius_sync.sync_equipment(db, e, manufacturer=m)
    db.flush()
    assert db.query(Nas).filter_by(nasname="10.2.2.2").first() is None


def test_regenerate_noop_without_path(db, seeded, mfr):
    # settings.tacacs_hosts_path é None nos testes => no-op, sem exceção
    assert tacacs_sync.regenerate(db) == 0


# ── nível de rota ──────────────────────────────────────────────────────


def test_equipment_route_tacacs_inheritance(auth_client, seeded):
    mid = auth_client.post("/api/manufacturers", json={
        "name": "cisco-x", "display_name": "Cisco X", "vendor_kind": "generic",
        "aaa_protocol": "tacacs", "tacacs_key": "cisco-grp-key",
    }).json()["id"]

    r = auth_client.post("/api/equipment", json={
        "name": "sw-tac", "mgmt_ip": "10.20.20.20", "manufacturer_id": mid,
        "shortname": "swtac",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["effective_protocol"] == "tacacs"
    assert body["protocol_source"] == "manufacturer"
    assert body["tacacs_key_source"] == "manufacturer"

    # sem chave em lado nenhum => 422
    mid2 = auth_client.post("/api/manufacturers", json={
        "name": "cisco-y", "display_name": "Cisco Y", "vendor_kind": "generic",
        "aaa_protocol": "tacacs",
    }).json()["id"]
    r = auth_client.post("/api/equipment", json={
        "name": "sw-y", "mgmt_ip": "10.20.20.21", "manufacturer_id": mid2, "shortname": "swy",
    })
    assert r.status_code == 422
    assert "TACACS+" in r.json()["detail"]


def test_olt_zte_route_tacacs(auth_client, seeded, db):
    mid = auth_client.post("/api/manufacturers", json={
        "name": "zte-t", "display_name": "ZTE T", "vendor_kind": "zte",
        "aaa_protocol": "tacacs", "tacacs_key": "zte-grp-key",
    }).json()["id"]

    r = auth_client.post("/api/equipment", json={
        "name": "olt-zte-01", "mgmt_ip": "10.30.30.30", "manufacturer_id": mid,
        "shortname": "oltzte01",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["vendor_kind"] == "zte"
    assert body["effective_protocol"] == "tacacs"
    assert body["tacacs_key_source"] == "manufacturer"

    text, n = tacacs_sync.build_config(db)
    assert n == 1
    assert "address = 10.30.30.30" in text
    assert 'key = "zte-grp-key"' in text


def test_switch_dell_route_tacacs(auth_client, seeded, db):
    mid = auth_client.post("/api/manufacturers", json={
        "name": "dell-t", "display_name": "Dell T", "vendor_kind": "dell",
        "aaa_protocol": "tacacs", "tacacs_key": "dell-grp-key",
    }).json()["id"]

    r = auth_client.post("/api/equipment", json={
        "name": "dellmogi", "mgmt_ip": "10.100.100.142", "manufacturer_id": mid,
        "shortname": "dellmogi",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["vendor_kind"] == "dell"
    assert body["effective_protocol"] == "tacacs"
    assert body["tacacs_key_source"] == "manufacturer"

    text, n = tacacs_sync.build_config(db)
    assert n == 1
    assert "address = 10.100.100.142" in text
    assert 'key = "dell-grp-key"' in text


def test_profile_route_tacacs_fields(auth_client, seeded):
    pid = auth_client.post("/api/privilege-profiles", json={
        "name": "net-admin", "tacacs_priv_level": 15,
        "tacacs_extra_avpairs": "shell:roles=network-admin",
    }).json()["id"]
    got = auth_client.get("/api/privilege-profiles").json()
    p = next(x for x in got if x["id"] == pid)
    assert p["tacacs_priv_level"] == 15
    assert p["tacacs_extra_avpairs"] == "shell:roles=network-admin"
