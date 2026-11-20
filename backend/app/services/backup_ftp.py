"""Backup automático agendado por FTP/FTPS do banco inteiro, com retenção no destino.

Quem executa é o container `backup-worker` (`app/backup_worker.py`); a API só grava
a configuração, testa a conexão e pede uma execução imediata (`run_requested_at`).

O arquivo é o mesmo do "Baixar backup" (`services/backup.dump_sql`): `.sql.enc`
cifrado com a FERNET_KEY ou `.sql.gz` em claro — ambos restauráveis em Backup e
restauração. Nada fica no servidor: o arquivo é gerado numa pasta temporária,
enviado e apagado; sobras de uma execução interrompida somem quando o worker inicia.
"""

from __future__ import annotations

import contextlib
import ftplib
import gzip
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.crypto import decrypt
from app.core.logging import logger
from app.core.security import utcnow
from app.models import BackupSchedule
from app.services import audit, backup

DEFAULT_TIMEZONE = "America/Sao_Paulo"
FILE_PREFIX = "h2node-auth-backup"
TEMP_PREFIX = "h2node-auth-ftp-"
# Nomes de antes do rebranding (Pulse RADIUS): entram na retenção como os novos.
LEGACY_FILE_PREFIXES = ("pulse-radius-backup",)
LEGACY_TEMP_PREFIXES = ("pulse-radius-ftp-",)
_PREFIXES_RE = "|".join(re.escape(p) for p in (FILE_PREFIX, *LEGACY_FILE_PREFIXES))
BACKUP_NAME_RE = re.compile(rf"^(?:{_PREFIXES_RE})-\d{{8}}-\d{{6}}\.sql\.(?:enc|gz)$")
_STAMP_RE = re.compile(r"\d{8}-\d{6}")
# Se o worker estava parado no horário, ainda roda até este tempo depois; mais que
# isso espera o dia seguinte (evita um dump pesado no meio do expediente).
CATCH_UP = timedelta(hours=6)
FTP_TIMEOUT_SECONDS = 60
AUDIT_ENTITY = "backup_schedule"
SYSTEM_ACTOR = "sistema"


class BackupFtpError(RuntimeError):
    """Configuração incompleta ou falha conferida pelo próprio backup."""


def get_schedule(db: Session) -> BackupSchedule | None:
    return db.execute(select(BackupSchedule).order_by(BackupSchedule.id)).scalars().first()


def default_schedule() -> BackupSchedule:
    """Transitória com os padrões (defaults de coluna só valem no INSERT)."""
    return BackupSchedule(
        enabled=False, run_time="02:30", timezone=DEFAULT_TIMEZONE, include_accounting=True,
        encrypted=True, keep_count=7, ftp_port=21, ftp_tls=True, ftp_write_only=False,
    )


def zone(cfg: BackupSchedule) -> ZoneInfo:
    try:
        return ZoneInfo(cfg.timezone or DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


# --- agenda -------------------------------------------------------------------------

def scheduled_utc(cfg: BackupSchedule, now_utc: datetime) -> datetime:
    """Horário de hoje (no fuso da agenda) em UTC naive, como as colunas DATETIME."""
    tz = zone(cfg)
    hour, minute = (int(part) for part in cfg.run_time.split(":"))
    local_now = now_utc.replace(tzinfo=UTC).astimezone(tz)
    local_run = datetime.combine(local_now.date(), time(hour, minute), tzinfo=tz)
    return local_run.astimezone(UTC).replace(tzinfo=None)


def next_run_utc(cfg: BackupSchedule, now_utc: datetime) -> datetime | None:
    if not cfg.enabled:
        return None
    today = scheduled_utc(cfg, now_utc)
    done_today = cfg.last_attempt_at is not None and cfg.last_attempt_at >= today
    if done_today or now_utc >= today + CATCH_UP:
        return scheduled_utc(cfg, now_utc + timedelta(days=1))
    return today


def is_due(cfg: BackupSchedule, now_utc: datetime) -> bool:
    if cfg.run_requested_at is not None:
        return True
    if not cfg.enabled:
        return False
    run_at = scheduled_utc(cfg, now_utc)
    if not run_at <= now_utc < run_at + CATCH_UP:
        return False
    return cfg.last_attempt_at is None or cfg.last_attempt_at < run_at


def missing_config(cfg: BackupSchedule) -> str | None:
    if not cfg.ftp_host:
        return "servidor FTP não configurado"
    return None


# --- FTP ----------------------------------------------------------------------------

def connect(cfg: BackupSchedule, password: str | None = None) -> ftplib.FTP:
    if password is None:
        password = ftp_password(cfg)
    client = (
        ftplib.FTP_TLS(timeout=FTP_TIMEOUT_SECONDS) if cfg.ftp_tls
        else ftplib.FTP(timeout=FTP_TIMEOUT_SECONDS)
    )
    client.connect(cfg.ftp_host or "", cfg.ftp_port or 21)
    client.login(cfg.ftp_user or "anonymous", password)
    if isinstance(client, ftplib.FTP_TLS):
        client.prot_p()  # canal de dados também cifrado
    client.set_pasv(True)
    _guard_data_channel(client)
    change_directory(client, cfg.ftp_directory, create=True)
    return client


def _guard_data_channel(client: ftplib.FTP) -> None:
    """Troca o `TimeoutError: timed out` cru por uma mensagem acionável quando a
    porta de dados anunciada no PASV não abre — o caso típico é o firewall do
    servidor liberar a porta 21 mas não a faixa passiva."""
    makepasv, ntransfercmd = client.makepasv, client.ntransfercmd
    endpoint: dict[str, tuple[str, int]] = {}

    def _makepasv():
        endpoint["data"] = makepasv()
        return endpoint["data"]

    def _ntransfercmd(cmd, rest=None):
        try:
            return ntransfercmd(cmd, rest)
        except (TimeoutError, ConnectionRefusedError) as exc:
            host, port = endpoint.get("data", ("?", 0))
            raise BackupFtpError(
                f"o servidor FTP aceitou o login, mas a porta de dados passiva {host}:{port} não "
                f"respondeu ({type(exc).__name__}). Libere no firewall do servidor FTP a faixa de "
                "portas passivas para o IP deste servidor — no H2NODE Backup, 30000-30049 "
                "(FTP_PASSIVE_PORTS): scripts/ufw-setup.sh device <IP> ftp. Atrás de NAT, confira "
                "também o FTP_MASQUERADE_ADDRESS."
            ) from exc

    client.makepasv = _makepasv  # type: ignore[method-assign]
    client.ntransfercmd = _ntransfercmd  # type: ignore[method-assign]


def ftp_password(cfg: BackupSchedule) -> str:
    if not cfg.ftp_password_enc:
        return ""
    try:
        return decrypt(cfg.ftp_password_enc)
    except Exception as exc:  # noqa: BLE001 - Fernet levanta InvalidToken
        raise BackupFtpError(
            "não foi possível decifrar a senha FTP guardada (FERNET_KEY mudou?) — informe-a de novo"
        ) from exc


def change_directory(client: ftplib.FTP, directory: str | None, create: bool = False) -> None:
    path = (directory or "").strip()
    if path.startswith("/"):
        client.cwd("/")
    for segment in [part for part in path.split("/") if part]:
        try:
            client.cwd(segment)
        except ftplib.error_perm:
            if not create:
                raise
            client.mkd(segment)
            client.cwd(segment)


def upload(client: ftplib.FTP, local_path: Path, remote_name: str, write_only: bool = False) -> None:
    if write_only:
        # Destino só de gravação (ex.: H2NODE Backup): não aceita SIZE, DELE nem
        # renomear. Vai direto com o nome final; o 226 do STOR confirma o recebimento.
        with open(local_path, "rb") as handle:
            client.storbinary(f"STOR {remote_name}", handle)
        return
    partial = f"{remote_name}.part"
    with open(local_path, "rb") as handle:
        client.storbinary(f"STOR {partial}", handle)
    expected = local_path.stat().st_size
    try:
        client.voidcmd("TYPE I")
        remote_size = client.size(partial)
    except ftplib.error_perm:
        remote_size = None  # servidor sem SIZE: confia no 226 do STOR
    if remote_size is not None and remote_size != expected:
        raise BackupFtpError(f"{remote_name}: enviado com {remote_size} bytes, esperado {expected}")
    with contextlib.suppress(ftplib.error_perm):
        client.delete(remote_name)
    client.rename(partial, remote_name)


def list_backups(client: ftplib.FTP) -> list[str]:
    try:
        names = client.nlst()
    except ftplib.error_perm:
        return []  # alguns servidores respondem 550 para pasta vazia
    return [n for n in (name.rsplit("/", 1)[-1] for name in names) if BACKUP_NAME_RE.match(n)]


def _stamp_of(name: str) -> str:
    m = _STAMP_RE.search(name)
    return m.group(0) if m else ""


def prune(client: ftplib.FTP, keep_count: int) -> list[str]:
    """Mantém só as `keep_count` cópias mais recentes. Devolve as apagadas."""
    removed = []
    # Ordena pelo carimbo AAAAMMDD-HHMMSS (não pelo nome inteiro): com o prefixo
    # antigo (pulse-radius-backup) e o novo na mesma pasta, a ordem alfabética
    # deixaria de ser a cronológica.
    for name in sorted(list_backups(client), key=_stamp_of, reverse=True)[keep_count:]:
        client.delete(name)
        removed.append(name)
    return removed


def close(client: ftplib.FTP) -> None:
    try:
        client.quit()
    except Exception:  # noqa: BLE001
        client.close()


def test_connection(cfg: BackupSchedule, password: str | None = None) -> int | None:
    """Conecta, entra (ou cria) a pasta e abre o canal de dados (listando a pasta).
    Devolve quantos backups há nela; None = só gravação."""
    client = connect(cfg, password)
    try:
        if not cfg.ftp_write_only:
            return len(list_backups(client))
        # Só gravação recusa a listagem, mas o ftplib abre a conexão de dados
        # (PASV + connect) antes de mandar o NLST: um 550 aqui prova que o canal
        # de dados funciona; firewall fechado vira o BackupFtpError do guard.
        with contextlib.suppress(ftplib.error_perm):
            client.nlst()
        return None
    finally:
        close(client)


# --- execução -----------------------------------------------------------------------

@dataclass
class BackupResult:
    uploaded: str = ""
    size: int = 0
    removed: list[str] = field(default_factory=list)

    def summary(self) -> str:
        msg = f"enviado {self.uploaded} ({_human(self.size)})"
        if self.removed:
            msg += f"; {len(self.removed)} cópia(s) antiga(s) apagada(s)"
        return msg


def _human(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB"):
        if value < 1024:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def write_dump(engine: Engine, cfg: BackupSchedule, path: Path, version: str | None) -> None:
    dump = backup.dump_sql(
        engine, include_accounting=cfg.include_accounting, schema_version=version
    )
    if cfg.encrypted:
        with open(path, "wb") as out:
            for chunk in backup.encrypt_stream(dump):
                out.write(chunk)
    else:
        with gzip.open(path, "wt", encoding="utf-8", newline="") as out:
            for chunk in dump:
                out.write(chunk)


def run_backup(
    engine: Engine, cfg: BackupSchedule, version: str | None, now: datetime | None = None
) -> BackupResult:
    """Gera e envia o backup. Levanta exceção em qualquer falha."""
    problem = missing_config(cfg)
    if problem:
        raise BackupFtpError(problem)
    password = ftp_password(cfg)  # falha cedo, antes do dump
    stamp = (now or datetime.now(zone(cfg))).strftime("%Y%m%d-%H%M%S")
    name = f"{FILE_PREFIX}-{stamp}.sql.{'enc' if cfg.encrypted else 'gz'}"
    result = BackupResult(uploaded=name)
    with tempfile.TemporaryDirectory(prefix=TEMP_PREFIX) as work:
        path = Path(work) / name
        write_dump(engine, cfg, path, version)
        result.size = path.stat().st_size
        client = connect(cfg, password)
        try:
            upload(client, path, name, write_only=cfg.ftp_write_only)
            path.unlink()
            # Só de gravação: não lista nem apaga; a retenção é a do servidor de backup.
            if not cfg.ftp_write_only:
                result.removed = prune(client, cfg.keep_count)
        finally:
            close(client)
    return result


def clean_leftovers(temp_dir: str | None = None) -> int:
    """Apaga pastas temporárias de backups interrompidos. Devolve quantas removeu."""
    removed = 0
    base = Path(temp_dir or tempfile.gettempdir())
    for prefix in (TEMP_PREFIX, *LEGACY_TEMP_PREFIXES):
        for path in base.glob(f"{prefix}*"):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                removed += 1
    return removed


def recover_interrupted(db: Session) -> bool:
    """No início do worker: uma execução presa em "running" morreu com o processo."""
    cfg = get_schedule(db)
    if cfg is None or cfg.last_status != "running":
        return False
    cfg.last_status = "error"
    cfg.last_message = "execução interrompida (o worker foi reiniciado durante o backup)"
    db.commit()
    return True


def reset_after_restore(db: Session) -> None:
    """O dump é gerado durante a execução, então a linha restaurada de um backup
    automático vem com last_status="running" — o que travaria o "Executar agora"."""
    cfg = get_schedule(db)
    if cfg is None or cfg.last_status != "running":
        return
    cfg.last_status = None
    cfg.last_message = "estado restaurado de um backup gerado durante a execução — veja a Auditoria"
    db.commit()


def describe_error(exc: BaseException) -> str:
    text = str(exc).strip()
    if isinstance(exc, ftplib.error_perm) and text.startswith("530"):
        return f"login FTP recusado: {text}"
    if isinstance(exc, ftplib.error_perm) and text.startswith("550"):
        return (
            f"permissão negada no FTP: {text} — se o destino só aceita gravação "
            "(ex.: H2NODE Backup), marque “Destino só de gravação”"
        )
    if isinstance(exc, BackupFtpError | backup.BackupError):
        return text
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


def execute(db: Session, engine: Engine) -> bool:
    """Uma rodada do worker: roda se estiver na hora ou se foi pedido. True se rodou."""
    cfg = get_schedule(db)
    now_utc = utcnow()
    if cfg is None or not is_due(cfg, now_utc):
        return False
    requested = cfg.run_requested_at is not None
    cfg.run_requested_at = None
    cfg.last_attempt_at = now_utc
    cfg.last_status = "running"
    cfg.last_message = None
    db.commit()
    logger.info("backup_ftp_started", trigger="manual" if requested else "schedule")

    version = backup.read_schema_version(db)
    db.commit()  # não segura transação aberta durante o dump
    try:
        result = run_backup(engine, cfg, version)
        status, message = "success", result.summary()
    except Exception as exc:  # noqa: BLE001 - não pode deixar o status preso em "running"
        status, message = "error", describe_error(exc)
        if not isinstance(exc, OSError | EOFError | ftplib.Error | BackupFtpError | backup.BackupError):
            logger.exception("backup_ftp_unexpected_error")
    db.rollback()

    cfg = get_schedule(db)
    if cfg is None:  # apagada durante a execução (ex.: restauração de backup)
        return True
    cfg.last_status = status
    cfg.last_message = message[:2000]
    if status == "success":
        cfg.last_success_at = utcnow()
    audit.record(
        db, action="backup_success" if status == "success" else "backup_error",
        entity_type=AUDIT_ENTITY, entity_id=cfg.id, actor_username=SYSTEM_ACTOR,
        after={"trigger": "manual" if requested else "schedule", "message": cfg.last_message,
               "host": cfg.ftp_host, "directory": cfg.ftp_directory},
    )
    db.commit()
    (logger.info if status == "success" else logger.error)("backup_ftp_finished", status=status,
                                                            message=message)
    return True
