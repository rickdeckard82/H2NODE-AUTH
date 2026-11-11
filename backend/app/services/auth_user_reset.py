"""Redefinição de senha de usuários de autenticação (RADIUS) por link enviado
por e-mail. O usuário não tem login no painel; o link abre uma página pública."""

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import utcnow
from app.models import AuthUser, AuthUserReset
from app.services import mailer

RESET_TTL_HOURS = 2


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_reset(db: Session, user: AuthUser) -> str:
    for pending in db.execute(
        select(AuthUserReset).where(
            AuthUserReset.auth_user_id == user.id, AuthUserReset.used_at.is_(None)
        )
    ).scalars():
        pending.used_at = utcnow()
    token = secrets.token_urlsafe(32)
    db.add(
        AuthUserReset(
            auth_user_id=user.id,
            token_hash=_hash(token),
            expires_at=utcnow() + timedelta(hours=RESET_TTL_HOURS),
        )
    )
    db.flush()
    return token


def resolve_reset(db: Session, token: str) -> AuthUserReset | None:
    row = db.execute(
        select(AuthUserReset).where(AuthUserReset.token_hash == _hash(token))
    ).scalar_one_or_none()
    if row is None or row.used_at is not None or row.expires_at < utcnow():
        return None
    return row


def send_reset_email(db: Session, user: AuthUser, token: str) -> None:
    link = f"{settings.frontend_origin.rstrip('/')}/reset-password?token={token}"
    name = user.full_name or user.username
    text = (
        f"Olá, {name}.\n\n"
        f"Foi solicitada a redefinição da senha de acesso aos equipamentos "
        f"({user.username}).\nPara criar uma nova senha, acesse:\n{link}\n\n"
        f"Este link expira em {RESET_TTL_HOURS} horas."
    )
    html = (
        f"<p>Olá, {name}.</p>"
        f"<p>Foi solicitada a redefinição da senha de acesso aos equipamentos "
        f"(usuário <code>{user.username}</code>).</p>"
        f'<p>Para criar uma nova senha, <a href="{link}">clique aqui</a>.</p>'
        f'<p style="color:#64748b;font-size:13px">Este link expira em '
        f"{RESET_TTL_HOURS} horas. Se você não esperava este e-mail, ignore-o.</p>"
    )
    mailer.send_mail(
        db, to=user.email, subject="Pulse RADIUS — redefinição de senha", html=html, text=text
    )
