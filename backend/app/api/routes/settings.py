from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import client_ip, enforce_csrf, require_superadmin
from app.core.crypto import encrypt
from app.core.db import get_db
from app.models import SmtpSettings, SystemUser
from app.schemas.smtp_settings import SmtpSettingsIn, SmtpSettingsOut, SmtpTestIn
from app.services import audit, mailer

router = APIRouter(prefix="/settings", tags=["settings"])


def _to_out(cfg: SmtpSettings) -> SmtpSettingsOut:
    return SmtpSettingsOut(
        id=cfg.id, host=cfg.host, port=cfg.port, username=cfg.username,
        has_password=bool(cfg.password_enc), use_tls=cfg.use_tls, use_ssl=cfg.use_ssl,
        from_email=cfg.from_email, from_name=cfg.from_name, updated_at=cfg.updated_at,
    )


@router.get("/smtp", response_model=SmtpSettingsOut | None)
def get_smtp(
    db: Session = Depends(get_db), _: SystemUser = Depends(require_superadmin)
) -> SmtpSettingsOut | None:
    cfg = mailer.get_settings(db)
    return _to_out(cfg) if cfg else None


@router.put("/smtp", response_model=SmtpSettingsOut, dependencies=[Depends(enforce_csrf)])
def put_smtp(
    body: SmtpSettingsIn, request: Request,
    db: Session = Depends(get_db), actor: SystemUser = Depends(require_superadmin),
) -> SmtpSettingsOut:
    cfg = mailer.get_settings(db)
    creating = cfg is None
    if cfg is None:
        cfg = SmtpSettings(host=body.host, from_email=body.from_email)
        db.add(cfg)

    cfg.host = body.host
    cfg.port = body.port
    cfg.username = body.username
    cfg.use_tls = body.use_tls
    cfg.use_ssl = body.use_ssl
    cfg.from_email = body.from_email
    cfg.from_name = body.from_name
    if body.clear_password:
        cfg.password_enc = None
    elif body.password:
        cfg.password_enc = encrypt(body.password)
    db.flush()

    audit.record(
        db, action="create" if creating else "update", entity_type="smtp_settings", entity_id=cfg.id,
        actor_id=actor.id, actor_username=actor.username, ip_address=client_ip(request),
        after={"host": cfg.host, "port": cfg.port, "use_tls": cfg.use_tls, "use_ssl": cfg.use_ssl},
    )
    db.commit()
    db.refresh(cfg)
    return _to_out(cfg)


@router.post("/smtp/test", dependencies=[Depends(enforce_csrf)])
def test_smtp(
    body: SmtpTestIn, db: Session = Depends(get_db), actor: SystemUser = Depends(require_superadmin)
) -> dict:
    try:
        mailer.send_mail(
            db, to=body.to, subject="Pulse RADIUS — e-mail de teste",
            html="<p>Se você recebeu este e-mail, o SMTP do Pulse RADIUS está configurado corretamente.</p>",
            text="Se você recebeu este e-mail, o SMTP do Pulse RADIUS está configurado corretamente.",
        )
    except mailer.SmtpNotConfigured as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except mailer.SmtpSendError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"falha ao enviar: {exc}") from exc
    return {"detail": f"e-mail de teste enviado para {body.to}"}
