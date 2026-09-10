"""Convite por e-mail para o usuário do painel concluir o cadastro criando a
própria senha (SystemUser.password_hash fica NULL até lá)."""

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import utcnow
from app.models import SystemUser, UserInvite
from app.services import mailer

INVITE_TTL_HOURS = 72


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_invite(db: Session, user: SystemUser) -> str:
    """Cria um novo convite (invalidando os anteriores) e devolve o token em claro."""
    for pending in db.execute(
        select(UserInvite).where(UserInvite.system_user_id == user.id, UserInvite.used_at.is_(None))
    ).scalars():
        pending.used_at = utcnow()  # invalida — só um convite ativo por vez

    token = secrets.token_urlsafe(32)
    db.add(
        UserInvite(
            system_user_id=user.id,
            token_hash=_hash(token),
            expires_at=utcnow() + timedelta(hours=INVITE_TTL_HOURS),
        )
    )
    db.flush()
    return token


def resolve_invite(db: Session, token: str) -> UserInvite | None:
    invite = db.execute(
        select(UserInvite).where(UserInvite.token_hash == _hash(token))
    ).scalar_one_or_none()
    if invite is None or invite.used_at is not None or invite.expires_at < utcnow():
        return None
    return invite


def send_invite_email(db: Session, user: SystemUser, token: str) -> None:
    link = f"{settings.frontend_origin.rstrip('/')}/set-password?token={token}"
    text = (
        f"Olá, {user.full_name}.\n\n"
        f"Uma conta foi criada para você no Pulse RADIUS ({user.username}).\n"
        f"Para concluir o cadastro e definir sua senha, acesse:\n{link}\n\n"
        f"Este link expira em {INVITE_TTL_HOURS} horas."
    )
    html = (
        f"<p>Olá, {user.full_name}.</p>"
        f"<p>Uma conta foi criada para você no <strong>Pulse RADIUS</strong> "
        f"(usuário <code>{user.username}</code>).</p>"
        f"<p>Para concluir o cadastro e definir sua senha, "
        f'<a href="{link}">clique aqui</a>.</p>'
        f"<p style=\"color:#64748b;font-size:13px\">Este link expira em "
        f"{INVITE_TTL_HOURS} horas. Se você não esperava este e-mail, ignore-o.</p>"
    )
    mailer.send_mail(
        db, to=user.email, subject="Pulse RADIUS — finalize seu cadastro", html=html, text=text
    )
