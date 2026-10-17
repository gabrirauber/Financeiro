"""Aprovação de acesso ao aplicativo, separada da participação em espaços."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import delete, select

from app.identity.dependencies import CurrentUser, Db
from app.identity.models import LoginSession, User

router = APIRouter(prefix="/admin/users", tags=["access-admin"])


class AccessDecision(BaseModel):
    status: Literal["approved", "rejected", "revoked"]


def require_access_admin(user: User):
    if not user.is_access_admin:
        raise HTTPException(403, "Somente o administrador de acesso pode fazer isso.")


def serialize_user(user: User):
    return {
        "id": user.id,
        "email": user.email,
        "status": user.access_status,
        "requested_at": user.requested_at,
        "access_admin": user.is_access_admin,
        "demo": user.is_demo,
    }


@router.get("")
def list_users(db: Db, user: CurrentUser, response: Response):
    require_access_admin(user)
    response.headers["Cache-Control"] = "no-store"
    rows = db.scalars(select(User).order_by(User.requested_at.desc(), User.email)).all()
    return [serialize_user(item) for item in rows]


@router.patch("/{user_id}/access")
def decide_access(user_id: UUID, data: AccessDecision, db: Db, user: CurrentUser,
                  response: Response):
    require_access_admin(user)
    target = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if target is None:
        raise HTTPException(404, "Cadastro não encontrado.")
    if target.is_access_admin:
        raise HTTPException(409, "O acesso do administrador não pode ser alterado aqui.")
    if data.status == "rejected" and target.access_status != "pending":
        raise HTTPException(409, "Somente pedidos pendentes podem ser recusados.")
    if data.status == "revoked" and target.access_status != "approved":
        raise HTTPException(409, "Somente acessos ativos podem ser revogados.")
    target.access_status = data.status
    if data.status != "approved":
        db.execute(delete(LoginSession).where(LoginSession.user_id == target.id))
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return serialize_user(target)
