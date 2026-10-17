from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.identity.models import LoginSession, User
from app.identity.security import digest, now

bearer = HTTPBearer(auto_error=False)


def get_db(request: Request):
    with Session(request.app.state.engine, expire_on_commit=False) as db:
        yield db


Db = Annotated[Session, Depends(get_db)]


def current_user(
    db: Db, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    if credentials is None:
        raise HTTPException(401, "Entre para continuar.")
    session = db.get(LoginSession, digest(credentials.credentials))
    if session is None or session.expires_at <= now():
        raise HTTPException(401, "Sua sessão expirou. Entre novamente.")
    user = db.scalar(select(User).where(User.id == session.user_id))
    if user is None:
        raise HTTPException(401, "Entre novamente.")
    if user.access_status != "approved":
        raise HTTPException(401, "Seu acesso não está ativo. Entre novamente após a aprovação.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
