"""Backup automático por FTP. O dump real exige MySQL; aqui ele é substituído e o
FTP é um servidor falso em memória."""

import ftplib
from datetime import datetime
from pathlib import Path

import pytest

from app.core.crypto import decrypt
from app.models import AuditLog, BackupSchedule
from app.services import backup_ftp


class FakeFTP:
    """Servidor FTP mínimo: guarda os arquivos num dict por pasta."""

    instances: list["FakeFTP"] = []
    files: dict[str, bytes] = {}
    write_only = False
    data_blocked = False  # firewall fechando a faixa passiva

    def __init__(self, timeout=None):
        self.cwd_path = ""
        self.commands: list[str] = []
        self.logged = None
        FakeFTP.instances.append(self)

    def connect(self, host, port):
        self.host, self.port = host, port

    def login(self, user, password):
        if password == "errada":
            raise ftplib.error_perm("530 Login incorrect.")
        self.logged = (user, password)

    def prot_p(self):
        self.commands.append("PROT P")

    def set_pasv(self, value):
        pass

    def makepasv(self):
        return ("203.0.113.10", 30027)

    def ntransfercmd(self, cmd, rest=None):
        """Como o ftplib: PASV + conexão de dados ANTES de mandar o comando."""
        self.makepasv()
        if FakeFTP.data_blocked:
            raise TimeoutError("timed out")
        return None, None

    def cwd(self, segment):
        self.cwd_path = "" if segment == "/" else f"{self.cwd_path}/{segment}"

    def mkd(self, segment):
        self.commands.append(f"MKD {segment}")

    def storbinary(self, cmd, handle):
        self.ntransfercmd(cmd)
        self.commands.append(cmd)
        FakeFTP.files[cmd.split(" ", 1)[1]] = handle.read()

    def _deny(self):
        if FakeFTP.write_only:
            raise ftplib.error_perm("550 Permission denied.")

    def voidcmd(self, cmd):
        pass

    def size(self, name):
        self._deny()
        return len(FakeFTP.files[name])

    def delete(self, name):
        self._deny()
        self.commands.append(f"DELE {name}")
        if name not in FakeFTP.files:
            raise ftplib.error_perm("550 No such file.")
        del FakeFTP.files[name]

    def rename(self, src, dst):
        self._deny()
        FakeFTP.files[dst] = FakeFTP.files.pop(src)

    def nlst(self):
        self.ntransfercmd("NLST")
        self._deny()
        return list(FakeFTP.files)

    def quit(self):
        pass

    def close(self):
        pass


class FakeFTPTLS(FakeFTP):
    pass


@pytest.fixture(autouse=True)
def fake_ftp(monkeypatch):
    FakeFTP.instances = []
    FakeFTP.files = {}
    FakeFTP.write_only = False
    FakeFTP.data_blocked = False
    monkeypatch.setattr(backup_ftp.ftplib, "FTP", FakeFTP)
    monkeypatch.setattr(backup_ftp.ftplib, "FTP_TLS", FakeFTPTLS)
    return FakeFTP


@pytest.fixture
def fake_dump(monkeypatch):
    def write(engine, cfg, path: Path, version):
        path.write_bytes(b"-- H2NODE Auth backup v1\n" + b"x" * 100)

    monkeypatch.setattr(backup_ftp, "write_dump", write)


def _cfg(**kw) -> BackupSchedule:
    cfg = backup_ftp.default_schedule()
    cfg.ftp_host = "ftp.exemplo"
    for k, v in kw.items():
        setattr(cfg, k, v)
    return cfg


# --- agenda -------------------------------------------------------------------------

def test_scheduled_utc_uses_timezone():
    cfg = _cfg(run_time="02:30", timezone="America/Sao_Paulo")
    # 02:30 em São Paulo (UTC-3) = 05:30 UTC
    assert backup_ftp.scheduled_utc(cfg, datetime(2026, 10, 19, 12, 0)) == datetime(2026, 10, 19, 5, 30)


def test_is_due_window_and_once_per_day():
    cfg = _cfg(enabled=True, run_time="02:30")
    assert not backup_ftp.is_due(cfg, datetime(2026, 10, 19, 5, 29))
    assert backup_ftp.is_due(cfg, datetime(2026, 10, 19, 5, 30))
    assert backup_ftp.is_due(cfg, datetime(2026, 10, 19, 11, 29))
    assert not backup_ftp.is_due(cfg, datetime(2026, 10, 19, 11, 31))  # passou do CATCH_UP
    cfg.last_attempt_at = datetime(2026, 10, 19, 5, 31)
    assert not backup_ftp.is_due(cfg, datetime(2026, 10, 19, 6, 0))


def test_is_due_disabled_unless_requested():
    cfg = _cfg(enabled=False)
    assert not backup_ftp.is_due(cfg, datetime(2026, 10, 19, 5, 30))
    cfg.run_requested_at = datetime(2026, 10, 19, 15, 0)
    assert backup_ftp.is_due(cfg, datetime(2026, 10, 19, 15, 0))


def test_next_run_moves_to_tomorrow_after_run():
    cfg = _cfg(enabled=True, run_time="02:30")
    assert backup_ftp.next_run_utc(cfg, datetime(2026, 10, 19, 1, 0)) == datetime(2026, 10, 19, 5, 30)
    cfg.last_attempt_at = datetime(2026, 10, 19, 5, 30)
    assert backup_ftp.next_run_utc(cfg, datetime(2026, 10, 19, 6, 0)) == datetime(2026, 10, 20, 5, 30)
    assert backup_ftp.next_run_utc(_cfg(enabled=False), datetime(2026, 10, 19)) is None


# --- envio --------------------------------------------------------------------------

def test_run_backup_uploads_part_and_prunes(fake_dump):
    for day in range(1, 5):
        FakeFTP.files[f"h2node-auth-backup-202610{day:02d}-023000.sql.enc"] = b"old"
    FakeFTP.files["outro-arquivo.txt"] = b"keep"
    cfg = _cfg(keep_count=2, ftp_directory="/backups/pulse", ftp_tls=True)

    result = backup_ftp.run_backup(None, cfg, "0018", now=datetime(2026, 10, 19, 2, 30))

    assert result.uploaded == "h2node-auth-backup-20261019-023000.sql.enc"
    client = FakeFTP.instances[-1]
    assert "PROT P" in client.commands
    assert client.cwd_path == "/backups/pulse"
    assert f"STOR {result.uploaded}.part" in client.commands
    assert sorted(FakeFTP.files) == [
        "h2node-auth-backup-20261004-023000.sql.enc",
        "h2node-auth-backup-20261019-023000.sql.enc",
        "outro-arquivo.txt",
    ]
    assert len(result.removed) == 3


def test_prune_counts_legacy_pulse_names_by_date(fake_dump):
    """Cópias de antes do rebranding (pulse-radius-backup-*) entram na retenção pela data."""
    FakeFTP.files["pulse-radius-backup-20261017-023000.sql.enc"] = b"old"
    FakeFTP.files["pulse-radius-backup-20261018-023000.sql.enc"] = b"old"
    cfg = _cfg(keep_count=2)

    result = backup_ftp.run_backup(None, cfg, None, now=datetime(2026, 10, 19, 2, 30))

    assert sorted(FakeFTP.files) == [
        "h2node-auth-backup-20261019-023000.sql.enc",
        "pulse-radius-backup-20261018-023000.sql.enc",
    ]
    assert result.removed == ["pulse-radius-backup-20261017-023000.sql.enc"]


def test_run_backup_write_only_never_lists_or_deletes(fake_dump):
    FakeFTP.write_only = True
    FakeFTP.files["h2node-auth-backup-20261001-023000.sql.gz"] = b"old"
    cfg = _cfg(ftp_write_only=True, encrypted=False, keep_count=1)

    result = backup_ftp.run_backup(None, cfg, None, now=datetime(2026, 10, 19, 2, 30))

    assert result.uploaded.endswith(".sql.gz")
    assert FakeFTP.instances[-1].commands[-1] == f"STOR {result.uploaded}"
    assert "h2node-auth-backup-20261001-023000.sql.gz" in FakeFTP.files
    assert result.removed == []


def test_run_backup_leaves_no_local_copy(fake_dump, tmp_path, monkeypatch):
    monkeypatch.setattr(backup_ftp.tempfile, "tempdir", str(tmp_path))
    backup_ftp.run_backup(None, _cfg(), None)
    assert list(tmp_path.iterdir()) == []


def test_run_backup_requires_host():
    with pytest.raises(backup_ftp.BackupFtpError):
        backup_ftp.run_backup(None, _cfg(ftp_host=None), None)


def test_clean_leftovers(tmp_path):
    (tmp_path / f"{backup_ftp.TEMP_PREFIX}abc").mkdir()
    (tmp_path / "outra").mkdir()
    assert backup_ftp.clean_leftovers(str(tmp_path)) == 1
    assert (tmp_path / "outra").exists()


# --- worker -------------------------------------------------------------------------

def test_execute_records_success_and_audit(db, fake_dump):
    db.add(_cfg(run_requested_at=datetime(2026, 10, 19, 12, 0)))
    db.commit()

    assert backup_ftp.execute(db, None) is True

    cfg = db.query(BackupSchedule).one()
    assert cfg.last_status == "success"
    assert cfg.run_requested_at is None
    assert cfg.last_success_at is not None
    assert cfg.last_message.startswith("enviado h2node-auth-backup-")
    log = db.query(AuditLog).filter_by(entity_type="backup_schedule").one()
    assert log.action == "backup_success"
    assert log.actor_username == "sistema"
    assert backup_ftp.execute(db, None) is False  # nada pendente


def test_execute_records_error(db, fake_dump):
    from app.core.crypto import encrypt

    db.add(_cfg(run_requested_at=datetime(2026, 10, 19, 12, 0), ftp_password_enc=encrypt("errada")))
    db.commit()

    backup_ftp.execute(db, None)

    cfg = db.query(BackupSchedule).one()
    assert cfg.last_status == "error"
    assert cfg.last_message.startswith("login FTP recusado")
    assert db.query(AuditLog).filter_by(action="backup_error").count() == 1


def test_recover_interrupted(db):
    db.add(_cfg(last_status="running"))
    db.commit()
    assert backup_ftp.recover_interrupted(db) is True
    assert db.query(BackupSchedule).one().last_status == "error"


# --- API ----------------------------------------------------------------------------

_BODY = {
    "enabled": True, "run_time": "03:15", "timezone": "America/Sao_Paulo",
    "include_accounting": False, "encrypted": True, "keep_count": 10,
    "ftp_host": " ftp.exemplo ", "ftp_port": 2121, "ftp_user": "pulse",
    "ftp_password": "s3nha", "ftp_directory": "/backups", "ftp_tls": True,
    "ftp_write_only": False,
}


def test_schedule_requires_superadmin(client):
    assert client.get("/api/backup/schedule").status_code == 401


def test_get_schedule_defaults(auth_client):
    r = auth_client.get("/api/backup/schedule")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["run_time"] == "02:30"
    assert body["has_ftp_password"] is False
    assert body["next_run_at"] is None


def test_put_schedule_encrypts_password_and_audits(auth_client, seeded):
    r = auth_client.put("/api/backup/schedule", json=_BODY)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ftp_host"] == "ftp.exemplo"
    assert body["has_ftp_password"] is True
    assert "ftp_password" not in body and "ftp_password_enc" not in body
    assert body["next_run_at"] is not None

    cfg = seeded.query(BackupSchedule).one()
    assert decrypt(cfg.ftp_password_enc) == "s3nha"
    log = seeded.query(AuditLog).filter_by(entity_type="backup_schedule").one()
    assert "s3nha" not in (log.after_json or "")

    # senha em branco mantém a atual
    r = auth_client.put("/api/backup/schedule", json={**_BODY, "ftp_password": ""})
    seeded.refresh(cfg)
    assert decrypt(cfg.ftp_password_enc) == "s3nha"
    r = auth_client.put(
        "/api/backup/schedule", json={**_BODY, "ftp_password": "", "clear_ftp_password": True}
    )
    assert r.json()["has_ftp_password"] is False


def test_put_schedule_validation(auth_client):
    def put(**kw):
        return auth_client.put("/api/backup/schedule", json={**_BODY, **kw}).status_code

    assert put(ftp_host="") == 400
    assert put(run_time="25:00") == 422
    assert put(timezone="Marte/Base") == 422
    assert put(keep_count=0) == 422


def test_test_connection_uses_saved_password(auth_client):
    auth_client.put("/api/backup/schedule", json=_BODY)
    r = auth_client.post("/api/backup/schedule/test", json={**_BODY, "ftp_password": ""})
    assert r.status_code == 200, r.text
    assert FakeFTP.instances[-1].logged == ("pulse", "s3nha")
    assert "0 backup(s)" in r.json()["detail"]


def test_test_connection_reports_failure(auth_client):
    r = auth_client.post("/api/backup/schedule/test", json={**_BODY, "ftp_password": "errada"})
    assert r.status_code == 502
    assert "login FTP recusado" in r.json()["detail"]


def test_test_connection_write_only(auth_client):
    FakeFTP.write_only = True
    r = auth_client.post("/api/backup/schedule/test", json={**_BODY, "ftp_write_only": True})
    assert r.status_code == 200
    assert "só de gravação" in r.json()["detail"]


def test_run_requires_saved_config(auth_client):
    assert auth_client.post("/api/backup/schedule/run").status_code == 400


def test_run_501_on_sqlite(auth_client):
    auth_client.put("/api/backup/schedule", json=_BODY)
    assert auth_client.post("/api/backup/schedule/run").status_code == 501


def test_reset_after_restore_unlocks_running(db):
    db.add(_cfg(last_status="running"))
    db.commit()
    backup_ftp.reset_after_restore(db)
    cfg = db.query(BackupSchedule).one()
    assert cfg.last_status is None
    assert "restaurado" in cfg.last_message


def test_describe_error_hints_write_only():
    msg = backup_ftp.describe_error(ftplib.error_perm("550 Not enough privileges."))
    assert "Destino só de gravação" in msg


def test_blocked_passive_port_gives_actionable_error(fake_dump):
    FakeFTP.data_blocked = True
    with pytest.raises(backup_ftp.BackupFtpError) as exc:
        backup_ftp.run_backup(None, _cfg(ftp_write_only=True), None)
    msg = backup_ftp.describe_error(exc.value)
    assert "203.0.113.10:30027" in msg
    assert "30000-30049" in msg


def test_test_connection_write_only_probes_data_channel(auth_client):
    """Antes o teste só de gravação passava sem abrir o canal de dados."""
    FakeFTP.write_only = True
    FakeFTP.data_blocked = True
    r = auth_client.post("/api/backup/schedule/test", json={**_BODY, "ftp_write_only": True})
    assert r.status_code == 502
    assert "porta de dados passiva" in r.json()["detail"]
