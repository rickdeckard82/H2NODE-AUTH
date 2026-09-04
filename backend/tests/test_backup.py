"""A suíte roda em SQLite; aqui só cobrimos guardas de acesso e validação.
O caminho feliz (dump/restore) exige MySQL e é verificado manualmente."""

import pytest


def test_export_requires_auth(client):
    assert client.get("/api/backup/export").status_code == 401


def test_export_requires_superadmin(auth_client, seeded):
    from app.core.security import hash_password
    from app.models import SystemRole, SystemUser

    seeded.add(
        SystemUser(
            username="op", email="op@example.com", full_name="Op",
            role=SystemRole.operator, is_active=True,
            password_hash=hash_password("changeme-admin-123"),
        )
    )
    seeded.commit()
    r = auth_client.post("/api/auth/login", json={"username": "op", "password": "changeme-admin-123"})
    auth_client.headers.update({"X-CSRF-Token": r.json()["csrf_token"]})
    assert auth_client.get("/api/backup/export").status_code == 403


def test_export_501_on_sqlite(auth_client):
    # superadmin autenticado, mas o backup lógico só suporta MySQL
    assert auth_client.get("/api/backup/export").status_code == 501


def test_import_rejects_bad_confirmation(auth_client):
    r = auth_client.post(
        "/api/backup/import",
        data={"confirm": "sim"},
        files={"file": ("b.sql", b"-- Pulse RADIUS backup v1\n", "application/sql")},
    )
    assert r.status_code == 400


def test_import_501_on_sqlite_with_valid_confirmation(auth_client):
    r = auth_client.post(
        "/api/backup/import",
        data={"confirm": "RESTAURAR"},
        files={"file": ("b.sql", b"-- Pulse RADIUS backup v1\n", "application/sql")},
    )
    assert r.status_code == 501


def test_encrypt_decrypt_stream_roundtrip():
    """encrypt_stream/decrypt_to_text não dependem de MySQL — testados direto."""
    from app.services import backup as backup_service

    chunks = [
        "-- Pulse RADIUS backup v1\n",
        "DROP TABLE IF EXISTS `app_system_user`;\n",
        "INSERT INTO `app_system_user` VALUES (1,'admin');\n" * 50,  # bloco maior
        "-- restore complete\n",
    ]
    encrypted = b"".join(backup_service.encrypt_stream(iter(chunks)))
    assert backup_service.is_encrypted(encrypted)
    assert not backup_service.is_encrypted("".join(chunks).encode())

    restored = backup_service.decrypt_to_text(encrypted)
    assert restored == "".join(chunks)


def test_decrypt_rejects_corrupted_or_plaintext_input():
    from app.services import backup as backup_service

    with pytest.raises(backup_service.BackupError):
        backup_service.decrypt_to_text(b"-- Pulse RADIUS backup v1\nnot encrypted")

    encrypted = b"".join(backup_service.encrypt_stream(iter(["hello"])))
    with pytest.raises(backup_service.BackupError):
        backup_service.decrypt_to_text(encrypted[:-5])  # trunca o último token
