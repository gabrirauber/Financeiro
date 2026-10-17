import hashlib
import secrets
import time
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from pwdlib import PasswordHash
from sqlalchemy import case
from sqlalchemy.dialects.postgresql import insert

from app.identity.models import LoginSession, RateLimit

passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash("dummy-password-not-a-user")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def now():
    return datetime.now(UTC)


def create_session(db, user_id, *, demo=False):
    token = secrets.token_urlsafe(32)
    expires = now() + (timedelta(hours=1) if demo else timedelta(days=30))
    db.add(LoginSession(token_hash=digest(token), user_id=user_id, expires_at=expires))
    return {"token": token, "expires_at": expires, "demo": demo}


def throttle(db, scope: str, identity: str, limit: int):
    window = int(time.time()) // 900
    statement = insert(RateLimit).values(key=digest(scope + identity), window=window, count=1)
    statement = statement.on_conflict_do_update(
        index_elements=[RateLimit.key],
        set_={
            "window": window,
            "count": case((RateLimit.window == window, RateLimit.count + 1), else_=1),
        },
    ).returning(RateLimit.count)
    count = db.scalar(statement)
    # Persistir tentativas inclusive se a autenticação falhar.
    db.commit()
    if count > limit:
        raise HTTPException(429, "Muitas tentativas. Aguarde alguns minutos.")
