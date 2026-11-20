import gzip
import io
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import client_ip, enforce_csrf, require_superadmin
from app.core.crypto import encrypt
from app.core.db import engine, get_db
from app.core.logging import logger
from app.core.security import utcnow
from app.models import BackupSchedule, SystemUser
from app.schemas.backup_schedule import BackupScheduleIn, BackupScheduleOut
from app.services import audit, backup, backup_ftp, tacacs_sync

router = APIRouter(
    prefix="/backup",
    tags=["backup"],
    dependencies=[Depends(enforce_csrf)],
)

# Teto do upload de restauração (o dump é texto SQL; 200 MB cobre bases grandes).
_MAX_UPLOAD = 200 * 1024 * 1024
_CONFIRM_WORD = "RESTAURAR"


def _schema_version(db: Session) -> str | None:
    return backup.read_schema_version(db)


def _gunzip(raw: bytes) -> bytes:
    """`.sql.gz` do backup automático por FTP. Limita o tamanho descompactado."""
    limit = _MAX_UPLOAD * 10
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
            data = gz.read(limit + 1)
    except (OSError, EOFError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "arquivo .gz corrompido") from exc
    if len(data) > limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "backup descompactado grande demais")
    return data


@router.get("/export")
def export_backup(
    request: Request,
    include_accounting: bool = True,
    encrypted: bool = True,
    db: Session = Depends(get_db),
    actor: SystemUser = Depends(require_superadmin),
) -> StreamingResponse:
    if engine.dialect.name != "mysql":
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "backup requer MySQL")

    version = _schema_version(db)
    audit.record(
        db, action="export", entity_type="backup",
        actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
        after={"include_accounting": include_accounting, "schema_version": version,
               "encrypted": encrypted},
    )
    db.commit()

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    dump = backup.dump_sql(engine, include_accounting=include_accounting, schema_version=version)
    if encrypted:
        filename = f"h2node-auth-backup-{stamp}.sql.enc"
        stream: StreamingResponse = StreamingResponse(
            backup.encrypt_stream(dump),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    else:
        filename = f"h2node-auth-backup-{stamp}.sql"
        stream = StreamingResponse(
            dump,
            media_type="application/sql",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return stream


@router.post("/import")
async def import_backup(
    request: Request,
    file: UploadFile = File(...),
    confirm: str = Form(...),
    db: Session = Depends(get_db),
    actor: SystemUser = Depends(require_superadmin),
) -> dict:
    if confirm != _CONFIRM_WORD:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f'digite "{_CONFIRM_WORD}" para confirmar')
    if engine.dialect.name != "mysql":
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "restauração requer MySQL")

    raw = await file.read()
    if len(raw) > _MAX_UPLOAD:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "arquivo maior que 200 MB")
    if raw[:2] == b"\x1f\x8b":  # .sql.gz do backup automático por FTP
        raw = _gunzip(raw)
    if backup.is_encrypted(raw):
        try:
            sql_text = backup.decrypt_to_text(raw)
        except backup.BackupError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    else:
        try:
            sql_text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "arquivo não é um backup válido") from exc

    current = _schema_version(db)
    # Libera a conexão/transação desta sessão ANTES do DDL: o DROP TABLE bloqueia
    # no metadata lock enquanto qualquer transação (incl. a do require_superadmin)
    # seguir aberta sobre as mesmas tabelas.
    actor_id, actor_username = actor.id, actor.username
    db.close()
    try:
        result = backup.restore_sql(engine, sql_text, current_version=current)
    except backup.BackupError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    # O dump cobre as tabelas (equipamentos, perfis, chaves...), mas o
    # /etc/tacacs-shared/h2node.cfg que o tac_plus-ng lê é um arquivo derivado,
    # fora do banco — sem isto ele ficaria com os hosts/perfis de antes da
    # restauração até a próxima edição de equipamento/perfil no painel.
    try:
        result["tacacs_hosts"] = tacacs_sync.regenerate(db)
    except Exception:  # noqa: BLE001 - não falha a restauração por causa disto
        logger.exception("tacacs_regenerate_after_restore_failed")
        result["tacacs_warning"] = (
            "restauração concluída, mas não foi possível regenerar a config do "
            "TACACS+ automaticamente — salve um equipamento ou perfil de "
            "privilégio qualquer no painel para forçar a regeneração."
        )

    try:
        backup_ftp.reset_after_restore(db)
    except Exception:  # noqa: BLE001 - não falha a restauração por causa disto
        db.rollback()
        logger.exception("backup_schedule_reset_after_restore_failed")

    # A restauração recriou app_audit_log a partir do arquivo; registra o evento
    # numa sessão nova (a anterior foi fechada acima).
    audit.record(
        db, action="import", entity_type="backup",
        actor_id=actor_id, actor_username=actor_username, ip_address=client_ip(request),
        after={"filename": file.filename, **result},
    )
    db.commit()
    return result


# ───────────────────── backup automático agendado por FTP ─────────────────────


def _schedule_out(cfg: BackupSchedule) -> BackupScheduleOut:
    return BackupScheduleOut(
        enabled=cfg.enabled, run_time=cfg.run_time, timezone=cfg.timezone,
        include_accounting=cfg.include_accounting, encrypted=cfg.encrypted,
        keep_count=cfg.keep_count, ftp_host=cfg.ftp_host, ftp_port=cfg.ftp_port,
        ftp_user=cfg.ftp_user, has_ftp_password=bool(cfg.ftp_password_enc),
        ftp_directory=cfg.ftp_directory, ftp_tls=cfg.ftp_tls, ftp_write_only=cfg.ftp_write_only,
        run_requested_at=cfg.run_requested_at, last_attempt_at=cfg.last_attempt_at,
        last_success_at=cfg.last_success_at, last_status=cfg.last_status,
        last_message=cfg.last_message, next_run_at=backup_ftp.next_run_utc(cfg, utcnow()),
    )


def _apply(cfg: BackupSchedule, body: BackupScheduleIn) -> None:
    cfg.enabled = body.enabled
    cfg.run_time = body.run_time
    cfg.timezone = body.timezone
    cfg.include_accounting = body.include_accounting
    cfg.encrypted = body.encrypted
    cfg.keep_count = body.keep_count
    cfg.ftp_host = body.ftp_host
    cfg.ftp_port = body.ftp_port
    cfg.ftp_user = body.ftp_user
    cfg.ftp_directory = body.ftp_directory
    cfg.ftp_tls = body.ftp_tls
    cfg.ftp_write_only = body.ftp_write_only
    if body.clear_ftp_password:
        cfg.ftp_password_enc = None
    elif body.ftp_password:
        cfg.ftp_password_enc = encrypt(body.ftp_password)


@router.get("/schedule", response_model=BackupScheduleOut)
def get_schedule(
    db: Session = Depends(get_db), _: SystemUser = Depends(require_superadmin)
) -> BackupScheduleOut:
    return _schedule_out(backup_ftp.get_schedule(db) or backup_ftp.default_schedule())


@router.put("/schedule", response_model=BackupScheduleOut)
def put_schedule(
    body: BackupScheduleIn, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_superadmin),
) -> BackupScheduleOut:
    if body.enabled and not body.ftp_host:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "informe o servidor FTP para ativar o agendamento")
    cfg = backup_ftp.get_schedule(db)
    creating = cfg is None
    if cfg is None:
        cfg = backup_ftp.default_schedule()
        db.add(cfg)
    _apply(cfg, body)
    db.flush()

    audit.record(
        db, action="create" if creating else "update", entity_type=backup_ftp.AUDIT_ENTITY,
        entity_id=cfg.id, actor_id=actor.id, actor_username=actor.username,
        ip_address=client_ip(request),
        after={
            "enabled": cfg.enabled, "run_time": cfg.run_time, "timezone": cfg.timezone,
            "include_accounting": cfg.include_accounting, "encrypted": cfg.encrypted,
            "keep_count": cfg.keep_count, "ftp_host": cfg.ftp_host, "ftp_port": cfg.ftp_port,
            "ftp_user": cfg.ftp_user, "ftp_directory": cfg.ftp_directory, "ftp_tls": cfg.ftp_tls,
            "ftp_write_only": cfg.ftp_write_only,
        },
    )
    db.commit()
    db.refresh(cfg)
    return _schedule_out(cfg)


@router.post("/schedule/test")
def test_schedule(
    body: BackupScheduleIn,
    db: Session = Depends(get_db), _: SystemUser = Depends(require_superadmin),
) -> dict:
    """Testa com os dados do formulário (ainda não salvos), sem gravar nada."""
    if not body.ftp_host:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "informe o servidor FTP")
    saved = backup_ftp.get_schedule(db)
    probe = backup_ftp.default_schedule()
    # Senha em branco no formulário = a já guardada.
    probe.ftp_password_enc = saved.ftp_password_enc if saved else None
    _apply(probe, body)
    db.rollback()
    try:
        existing = backup_ftp.test_connection(probe)
    except Exception as exc:  # noqa: BLE001 - devolve o motivo ao operador
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"falha na conexão: {backup_ftp.describe_error(exc)}"
        ) from exc
    if existing is None:
        return {
            "detail": "conexão OK. Destino só de gravação: as cópias antigas ficam no servidor de backup."
        }
    return {"detail": f"conexão OK. {existing} backup(s) do H2NODE Auth na pasta."}


@router.post("/schedule/run", response_model=BackupScheduleOut, status_code=status.HTTP_202_ACCEPTED)
def run_schedule(
    request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_superadmin),
) -> BackupScheduleOut:
    cfg = backup_ftp.get_schedule(db)
    problem = backup_ftp.missing_config(cfg) if cfg else "salve a configuração do backup antes de executar"
    if cfg is None or problem:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, problem)
    if engine.dialect.name != "mysql":
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "backup requer MySQL")
    cfg.run_requested_at = utcnow()
    audit.record(
        db, action="run_request", entity_type=backup_ftp.AUDIT_ENTITY, entity_id=cfg.id,
        actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(cfg)
    return _schedule_out(cfg)
