from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.identity.dependencies import CurrentUser, Db, bearer
from app.identity.models import LoginSession, Membership, User, Workspace
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


class Registration(Credentials):
    invite_code: str | None = Field(default=None, max_length=64)
    workspace_name: str | None = Field(default=None, max_length=80)

    @field_validator("invite_code", "workspace_name")
    @classmethod
    def clean_optional(cls, value):
        if value is None:
            return None
        return " ".join(value.split()) or None


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
def register(data: Registration, request: Request, response: Response, db: Db):
    limit_credentials(db, request, data.email)
    if data.invite_code and data.workspace_name:
        raise HTTPException(422, "Escolha criar seu espaço ou entrar com um código.")
    user = User(
        email=normalize(data.email), password_hash=passwords.hash(data.password.get_secret_value()),
        access_status="pending" if request.app.state.settings.approval_required else "approved",
    )
    db.add(user)
    try:
        db.flush()
        if data.invite_code:
            from app.identity.invites import claim_invite

            claim_invite(db, user, data.invite_code)
        elif data.workspace_name:
            from app.finance.categories import seed_categories

            workspace = Workspace(name=data.workspace_name)
            db.add(workspace)
            db.flush()
            db.add(Membership(workspace_id=workspace.id, user_id=user.id, role="admin"))
            seed_categories(db, workspace.id)
        result = (
            {"status": "pending"}
            if user.access_status == "pending" else create_session(db, user.id)
        )
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
    if user.access_status == "pending":
        raise HTTPException(403, "Seu cadastro aguarda aprovação para acessar o Rautto.")
    if user.access_status == "rejected":
        raise HTTPException(403, "Seu pedido de acesso não foi aprovado.")
    if user.access_status == "revoked":
        raise HTTPException(403, "Seu acesso ao Rautto foi revogado.")
    result = create_session(db, user.id)
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get("/me")
def me(user: CurrentUser):
    return {"id": user.id, "email": user.email,
            "access_admin": user.is_access_admin}


@router.post("/logout", status_code=204)
def logout(db: Db, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    if credentials:
        db.execute(
            delete(LoginSession).where(LoginSession.token_hash == digest(credentials.credentials))
        )
        db.commit()
