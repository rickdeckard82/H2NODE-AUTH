"""Redefinição de senha de usuários de autenticação (RADIUS) por link enviado
por e-mail. O usuário não tem login no painel; o link abre uma página pública."""

from html import escape

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AuthUser, AuthUserReset
from app.services import mailer, tokens

RESET_TTL_HOURS = 2


def create_reset(db: Session, user: AuthUser) -> str:
    return tokens.issue(db, AuthUserReset, "auth_user_id", user.id, RESET_TTL_HOURS)


def resolve_reset(db: Session, token: str) -> AuthUserReset | None:
    return tokens.resolve(db, AuthUserReset, token)


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
        f"<p>Olá, {escape(name)}.</p>"
        f"<p>Foi solicitada a redefinição da senha de acesso aos equipamentos "
        f"(usuário <code>{escape(user.username)}</code>).</p>"
        f'<p>Para criar uma nova senha, <a href="{link}">clique aqui</a>.</p>'
        f'<p style="color:#64748b;font-size:13px">Este link expira em '
        f"{RESET_TTL_HOURS} horas. Se você não esperava este e-mail, ignore-o.</p>"
    )
    mailer.send_mail(
        db, to=user.email, subject="H2NODE Auth — redefinição de senha", html=html, text=text
    )
