"""Retenção de dados (LGPD): exclusão automática conforme os prazos configurados.

`run_if_due()` é chamado pelo loop do `backup-worker` (processo único, fora do
caminho das requisições). A linha única de `app_lgpd_settings` serve de claim
atômico: só quem consegue avançar `last_purge_at` executa, no máximo 1x a cada 24h.
O claim é commitado antes e o expurgo apaga em lotes com commit a cada lote, para
não segurar lock em `radpostauth` (onde o FreeRADIUS grava cada login) nem
recomeçar do zero se o processo cair no meio.
"""

from datetime import timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.core.security import utcnow
from app.models import AuditLog, AuthUser, CmdAcct, LgpdSettings, RadAcct, RadPostAuth
from app.services import radius_sync

_MIN_INTERVAL = timedelta(hours=24)
_BATCH = 5000


def get_settings(db: Session) -> LgpdSettings | None:
    return db.execute(select(LgpdSettings)).scalars().first()


def _delete_batched(db: Session, pk, *where) -> int:
    """DELETE em lotes de _BATCH linhas, com commit a cada lote."""
    table = pk.class_
    total = 0
    while True:
        ids = db.execute(select(pk).where(*where).limit(_BATCH)).scalars().all()
        if not ids:
            return total
        db.execute(delete(table).where(pk.in_(ids)))
        db.commit()
        total += len(ids)


def purge(db: Session, cfg: LgpdSettings) -> dict[str, int]:
    """Apaga o que passou dos prazos, em lotes commitados."""
    now = utcnow()
    counts: dict[str, int] = {}

    if cfg.accounting_retention_days > 0:
        cut = now - timedelta(days=cfg.accounting_retention_days)
        counts["radpostauth"] = _delete_batched(db, RadPostAuth.id, RadPostAuth.authdate < cut)
        counts["cmd_acct"] = _delete_batched(db, CmdAcct.id, CmdAcct.event_time < cut)
        # radacct: só sessões já encerradas
        counts["radacct"] = _delete_batched(
            db, RadAcct.radacctid, RadAcct.acctstoptime.is_not(None), RadAcct.acctstoptime < cut
        )

    if cfg.audit_retention_days > 0:
        cut = now - timedelta(days=cfg.audit_retention_days)
        counts["audit_log"] = _delete_batched(db, AuditLog.id, AuditLog.created_at < cut)

    if cfg.auth_user_retention_days > 0:
        cut = now - timedelta(days=cfg.auth_user_retention_days)
        # Só usuários de autenticação DESATIVADOS e sem uso há mais de N dias
        # (last_auth_at, ou a última alteração como aproximação).
        last_seen = func.coalesce(AuthUser.last_auth_at, AuthUser.updated_at)
        stale = list(
            db.execute(
                select(AuthUser).where(AuthUser.is_active.is_(False), last_seen < cut)
            ).scalars()
        )
        for u in stale:
            radius_sync.delete_auth_user(db, u.username)
            db.delete(u)
        db.commit()
        counts["auth_user"] = len(stale)

    return {k: v for k, v in counts.items() if v}


def run_if_due(db: Session) -> dict[str, int] | None:
    """Se passou >=24h do último expurgo, reivindica a execução e roda. Nunca
    levanta exceção — o loop do backup-worker não pode morrer por causa dele."""
    try:
        cfg = get_settings(db)
        if cfg is None:
            return None
        if not (
            cfg.accounting_retention_days
            or cfg.audit_retention_days
            or cfg.auth_user_retention_days
        ):
            return None

        now = utcnow()
        threshold = now - _MIN_INTERVAL
        if cfg.last_purge_at is not None and cfg.last_purge_at >= threshold:
            return None  # ainda dentro da janela — nem tenta o claim

        claimed = db.execute(
            update(LgpdSettings)
            .where(
                LgpdSettings.id == cfg.id,
                (LgpdSettings.last_purge_at.is_(None))
                | (LgpdSettings.last_purge_at < threshold),
            )
            .values(last_purge_at=now)
        ).rowcount
        if not claimed:  # outro processo levou o claim
            db.rollback()
            return None
        db.commit()  # o claim vale mesmo se o expurgo cair no meio: tenta de novo em 24h

        counts = purge(db, cfg)
        if counts:
            logger.info("lgpd_retention_purge", **counts)
        return counts
    except Exception as exc:  # nunca quebra o endpoint que chamou
        db.rollback()
        logger.error("lgpd_retention_purge_failed", error=str(exc))
        return None
