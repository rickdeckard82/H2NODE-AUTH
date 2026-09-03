from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import client_ip, enforce_csrf, require_superadmin
from app.core.db import engine, get_db
from app.models import SystemUser
from app.services import audit, backup

router = APIRouter(
    prefix="/backup",
    tags=["backup"],
    dependencies=[Depends(enforce_csrf)],
)

# Teto do upload de restauração (o dump é texto SQL; 200 MB cobre bases grandes).
_MAX_UPLOAD = 200 * 1024 * 1024
_CONFIRM_WORD = "RESTAURAR"


def _schema_version(db: Session) -> str | None:
    try:
        return db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:  # noqa: BLE001 - tabela ausente / dialeto sem alembic
        return None


@router.get("/export")
def export_backup(
    request: Request,
    include_accounting: bool = True,
    db: Session = Depends(get_db),
    actor: SystemUser = Depends(require_superadmin),
) -> StreamingResponse:
    if engine.dialect.name != "mysql":
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "backup requer MySQL")

    version = _schema_version(db)
    audit.record(
        db, action="export", entity_type="backup",
        actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
        after={"include_accounting": include_accounting, "schema_version": version},
    )
    db.commit()

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    filename = f"pulse-radius-backup-{stamp}.sql"
    stream = backup.dump_sql(engine, include_accounting=include_accounting, schema_version=version)
    return StreamingResponse(
        stream,
        media_type="application/sql",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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

    # A restauração recriou app_audit_log a partir do arquivo; registra o evento
    # numa sessão nova (a anterior foi fechada acima).
    audit.record(
        db, action="import", entity_type="backup",
        actor_id=actor_id, actor_username=actor_username, ip_address=client_ip(request),
        after={"filename": file.filename, **result},
    )
    db.commit()
    return result
