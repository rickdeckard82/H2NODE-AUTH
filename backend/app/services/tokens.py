"""Links de uso único enviados por e-mail (convite/reset do painel, reset de
senha RADIUS). No banco fica só o SHA-256 do token; o valor em claro só existe
no link."""

import secrets
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.security import hash_token, utcnow

# UserInvite (owner: system_user_id) e AuthUserReset (owner: auth_user_id) têm as
# mesmas colunas token_hash / expires_at / used_at.


def issue(db: Session, model, owner_col: str, owner_id: int, ttl_hours: int) -> str:
    """Invalida os links pendentes do dono, cria um novo e devolve o token em claro."""
    owner = getattr(model, owner_col)
    for pending in db.execute(
        select(model).where(owner == owner_id, model.used_at.is_(None))
    ).scalars():
        pending.used_at = utcnow()  # só um link ativo por vez
    token = secrets.token_urlsafe(32)
    db.add(model(**{owner_col: owner_id}, token_hash=hash_token(token),
                 expires_at=utcnow() + timedelta(hours=ttl_hours)))
    db.flush()
    return token


def resolve(db: Session, model, token: str):
    row = db.execute(
        select(model).where(model.token_hash == hash_token(token))
    ).scalar_one_or_none()
    if row is None or row.used_at is not None or row.expires_at < utcnow():
        return None
    return row


def consume(db: Session, row) -> bool:
    """Marca como usado só se ainda não foi — dois "aceitar" simultâneos não
    usam o mesmo link. False => outro request levou."""
    model = type(row)
    now = utcnow()
    claimed = db.execute(
        update(model).where(model.id == row.id, model.used_at.is_(None))
        .values(used_at=now).execution_options(synchronize_session=False)
    ).rowcount
    if claimed:
        row.used_at = now
    return bool(claimed)
