"""Retenção de dados (LGPD): exclusão automática conforme os prazos configurados.

Roda de forma oportunista — `run_if_due()` é chamado de um endpoint frequente
(`/health`). A linha única de `app_lgpd_settings` serve de claim atômico entre os
workers do gunicorn: só quem consegue avançar `last_purge_at` executa o expurgo,
e no máximo uma vez a cada 24h.
"""

from datetime import timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.core.security import utcnow
from app.models import AuditLog, AuthUser, CmdAcct, LgpdSettings, RadAcct, RadPostAuth
from app.services import radius_sync

_MIN_INTERVAL = timedelta(hours=24)


def get_settings(db: Session) -> LgpdSettings | None:
    return db.execute(select(LgpdSettings)).scalars().first()


def purge(db: Session, cfg: LgpdSettings) -> dict[str, int]:
    """Apaga o que passou dos prazos. Sem commit — quem chama fecha a transação."""
    now = utcnow()
    counts: dict[str, int] = {}

    if cfg.accounting_retention_days > 0:
        cut = now - timedelta(days=cfg.accounting_retention_days)
        counts["radpostauth"] = db.execute(
            delete(RadPostAuth).where(RadPostAuth.authdate < cut)
        ).rowcount
        counts["cmd_acct"] = db.execute(
            delete(CmdAcct).where(CmdAcct.event_time < cut)
        ).rowcount
        # radacct: só sessões já encerradas
        counts["radacct"] = db.execute(
            delete(RadAcct).where(
                RadAcct.acctstoptime.is_not(None), RadAcct.acctstoptime < cut
            )
        ).rowcount

    if cfg.audit_retention_days > 0:
        cut = now - timedelta(days=cfg.audit_retention_days)
        counts["audit_log"] = db.execute(
            delete(AuditLog).where(AuditLog.created_at < cut)
        ).rowcount

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
        counts["auth_user"] = len(stale)

    return {k: v for k, v in counts.items() if v}


def run_if_due(db: Session) -> dict[str, int] | None:
    """Se passou >=24h do último expurgo, reivindica a execução e roda. Nunca
    levanta exceção — é chamado de dentro do `/health`."""
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
        if not claimed:  # outro worker levou o claim
            db.rollback()
            return None

        counts = purge(db, cfg)
        db.commit()
        if counts:
            logger.info("lgpd_retention_purge", **counts)
        return counts
    except Exception as exc:  # nunca quebra o endpoint que chamou
        db.rollback()
        logger.error("lgpd_retention_purge_failed", error=str(exc))
        return None
