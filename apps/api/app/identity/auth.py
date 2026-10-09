from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.identity.dependencies import CurrentUser, Db, bearer
from app.identity.models import LoginSession, User
from app.identity.security import DUMMY_HASH, create_session, digest, passwords, throttle

router = APIRouter(prefix="/auth", tags=["auth"])


class PasswordInput(BaseModel):
    password: SecretStr

    @field_validator("password")
    @classmethod
    def password_length(cls, value):
        if not 10 <= len(value.get_secret_value()) <= 128:
            raise ValueError("A senha deve ter de 10 a 128 caracteres.")
        return value


class Credentials(PasswordInput):
    email: EmailStr


class EmailInput(BaseModel):
    email: EmailStr


class NameInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("Informe um nome.")
        return value


def normalize(email):
    return str(email).strip().lower()


def limit_credentials(db, request, email):
    throttle(db, "auth-ip:", request.client.host if request.client else "unknown", 60)
    throttle(db, "auth-email:", normalize(email), 15)


@router.post("/register", status_code=201)
def register(data: Credentials, request: Request, response: Response, db: Db):
    limit_credentials(db, request, data.email)
    user = User(
        email=normalize(data.email), password_hash=passwords.hash(data.password.get_secret_value())
    )
    db.add(user)
    try:
        db.flush()
        result = create_session(db, user.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Não foi possível cadastrar este e-mail.") from None
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post("/login")
def login(data: Credentials, request: Request, response: Response, db: Db):
    limit_credentials(db, request, data.email)
    user = db.scalar(select(User).where(User.email == normalize(data.email)).with_for_update())
    correct = passwords.verify(
        data.password.get_secret_value(), user.password_hash if user else DUMMY_HASH
    )
    if not user or not correct:
        raise HTTPException(401, "E-mail ou senha inválidos.")
    result = create_session(db, user.id)
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get("/me")
def me(user: CurrentUser):
    return {"id": user.id, "email": user.email}


@router.post("/logout", status_code=204)
def logout(db: Db, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    if credentials:
        db.execute(
            delete(LoginSession).where(LoginSession.token_hash == digest(credentials.credentials))
        )
        db.commit()
