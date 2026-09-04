"""Envio de e-mail via SMTP configurado em Configurações (app_smtp_settings)."""

import smtplib
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import make_msgid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt
from app.models import SmtpSettings


class SmtpNotConfigured(Exception):
    pass


class SmtpSendError(Exception):
    pass


def get_settings(db: Session) -> SmtpSettings | None:
    return db.execute(select(SmtpSettings)).scalars().first()


def _from_header(cfg: SmtpSettings) -> str:
    if cfg.from_name:
        local, _, domain = cfg.from_email.partition("@")
        return str(Address(cfg.from_name, local, domain))
    return cfg.from_email


def send_mail(db: Session, *, to: str, subject: str, html: str, text: str) -> None:
    cfg = get_settings(db)
    if cfg is None or not cfg.host or not cfg.from_email:
        raise SmtpNotConfigured("SMTP não configurado — veja Configurações > SMTP")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _from_header(cfg)
    msg["To"] = to
    msg["Message-ID"] = make_msgid()
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    password = decrypt(cfg.password_enc) if cfg.password_enc else None
    try:
        if cfg.use_ssl:
            with smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=10) as smtp:
                if cfg.username:
                    smtp.login(cfg.username, password or "")
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(cfg.host, cfg.port, timeout=10) as smtp:
                if cfg.use_tls:
                    smtp.starttls()
                if cfg.username:
                    smtp.login(cfg.username, password or "")
                smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        raise SmtpSendError(str(exc)) from exc
