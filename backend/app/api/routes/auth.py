from datetime import timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_current_user
from app.core.config import settings
from app.core.db import get_db
from app.core.ratelimit import limiter
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    new_csrf_token,
    utcnow,
    verify_password,
)
from app.models import RefreshToken, SystemUser
from app.schemas.auth import LoginIn, MeOut, SessionOut
from app.services import audit

router = APIRouter(prefix="/auth", tags=["auth"])

_MAX_FAILED_LOGINS = 5
_LOCKOUT_MINUTES = 15
_TOKEN_GC_KEEP_DAYS = 1  # remove tokens expirados/revogados há mais de 1 dia


def _gc_refresh_tokens(db: Session) -> None:
    """Poda oportunista: limpa refresh tokens já expirados/revogados e antigos."""
    cutoff = utcnow() - timedelta(days=_TOKEN_GC_KEEP_DAYS)
    db.execute(
        delete(RefreshToken)
        .where(
            or_(
                RefreshToken.expires_at < cutoff,
                RefreshToken.revoked.is_(True),
            ),
            RefreshToken.issued_at < cutoff,
        )
        .execution_options(synchronize_session=False)
    )


def _set_auth_cookies(resp: Response, *, access: str, refresh: str, csrf: str) -> None:
    common = {
        "secure": settings.cookie_secure,
        "samesite": "strict",
        "domain": settings.cookie_domain,
    }
    resp.set_cookie(
        settings.access_cookie_name, access, httponly=True, path="/",
        max_age=settings.access_token_ttl_minutes * 60, **common,
    )
    resp.set_cookie(
        settings.refresh_cookie_name, refresh, httponly=True, path="/api/auth",
        max_age=settings.refresh_token_ttl_days * 86400, **common,
    )
    # CSRF: legível pelo JS (double-submit), portanto httponly=False
    resp.set_cookie(
        settings.csrf_cookie_name, csrf, httponly=False, path="/",
        max_age=settings.refresh_token_ttl_days * 86400, **common,
    )


def _clear_auth_cookies(resp: Response) -> None:
    for name, path in (
        (settings.access_cookie_name, "/"),
        (settings.refresh_cookie_name, "/api/auth"),
        (settings.csrf_cookie_name, "/"),
    ):
        resp.delete_cookie(name, path=path, domain=settings.cookie_domain)


def _issue_session(db: Session, resp: Response, user: SystemUser, request: Request) -> str:
    access = create_access_token(str(user.id), user.role.value)
    refresh, jti, exp = create_refresh_token(str(user.id))
    csrf = new_csrf_token()
    db.add(
        RefreshToken(
            jti=jti, system_user_id=user.id, expires_at=exp,
            user_agent=(request.headers.get("user-agent") or "")[:255] or None,
            ip_address=client_ip(request),
        )
    )
    _set_auth_cookies(resp, access=access, refresh=refresh, csrf=csrf)
    return csrf


@router.post("/login", response_model=SessionOut)
@limiter.limit("10/minute")
def login(
    body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)
) -> SessionOut:
    user = db.execute(
        select(SystemUser).where(SystemUser.username == body.username)
    ).scalar_one_or_none()

    # Conta bloqueada por tentativas malsucedidas.
    if user is not None and user.locked_until and user.locked_until > utcnow():
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "conta temporariamente bloqueada por excesso de tentativas; tente mais tarde",
        )

    # verify_password sempre executa (mesmo com user inexistente, contra um hash
    # descartável) para não vazar a existência da conta por diferença de tempo.
    password_ok = verify_password(
        body.password, user.password_hash if user else DUMMY_PASSWORD_HASH
    )

    if user is None or not password_ok:
        if user is not None:
            user.failed_login_count += 1
            if user.failed_login_count >= _MAX_FAILED_LOGINS:
                user.locked_until = utcnow() + timedelta(minutes=_LOCKOUT_MINUTES)
                user.failed_login_count = 0
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "credenciais inválidas")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "conta desativada")

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = utcnow()
    _gc_refresh_tokens(db)
    csrf = _issue_session(db, response, user, request)
    audit.record(
        db, action="login", entity_type="system_user", entity_id=user.id,
        actor_id=user.id, actor_username=user.username, ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return SessionOut(user=MeOut.model_validate(user), csrf_token=csrf)


@router.post("/refresh", response_model=SessionOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> SessionOut:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "sem refresh token")
    try:
        payload = decode_token(token, expected_type="refresh")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh inválido") from exc

    stored = db.execute(
        select(RefreshToken).where(RefreshToken.jti == payload["jti"])
    ).scalar_one_or_none()
    if stored is None or stored.revoked or stored.expires_at < utcnow():
        # reuso de token revogado => derruba toda a árvore de sessões do usuário
        if stored is not None:
            db.query(RefreshToken).filter(
                RefreshToken.system_user_id == stored.system_user_id,
                RefreshToken.revoked.is_(False),
            ).update({"revoked": True})
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh revogado")

    user = db.get(SystemUser, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "conta inativa")

    stored.revoked = True
    csrf = _issue_session(db, response, user, request)
    db.commit()
    return SessionOut(user=MeOut.model_validate(user), csrf_token=csrf)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    token = request.cookies.get(settings.refresh_cookie_name)
    if token:
        try:
            payload = decode_token(token, expected_type="refresh")
            db.query(RefreshToken).filter(RefreshToken.jti == payload["jti"]).update(
                {"revoked": True}
            )
            db.commit()
        except jwt.InvalidTokenError:
            pass
    _clear_auth_cookies(response)
    return {"detail": "sessão encerrada"}


@router.get("/me", response_model=MeOut)
def me(user: SystemUser = Depends(get_current_user)) -> MeOut:
    return MeOut.model_validate(user)
