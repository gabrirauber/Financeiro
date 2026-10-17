"""Aprovação de acesso ao aplicativo, separada da participação em espaços."""

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import delete, func, select, update

from app.finance.recurrence_models import IncomeOccurrence, IncomePlan
from app.identity.dependencies import CurrentUser, Db
from app.identity.models import Invite, LoginSession, Membership, User, Workspace

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


@router.delete("/{user_id}", status_code=204)
def delete_revoked_user(user_id: UUID, db: Db, user: CurrentUser, response: Response):
    require_access_admin(user)
    target = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if target is None:
        raise HTTPException(404, "Cadastro não encontrado.")
    if target.is_access_admin or target.is_demo:
        raise HTTPException(409, "Este cadastro protegido não pode ser excluído.")
    if target.access_status != "revoked":
        raise HTTPException(409, "Revogue o acesso antes de excluir o cadastro.")

    memberships = db.scalars(select(Membership).where(Membership.user_id == target.id)).all()
    own_workspaces = []
    for membership in memberships:
        if membership.role != "admin":
            continue
        member_count = db.scalar(select(func.count()).select_from(Membership).where(
            Membership.workspace_id == membership.workspace_id
        ))
        if member_count > 1:
            raise HTTPException(
                409,
                "Transfira a administração do espaço compartilhado antes de excluir o cadastro.",
            )
        own_workspaces.append(membership.workspace_id)

    # Planos compartilhados deixam de gerar cobranças futuras; histórico e
    # recebimentos já lançados permanecem no espaço dos demais participantes.
    plans = db.scalars(select(IncomePlan).where(
        IncomePlan.responsible_user_id == target.id,
        IncomePlan.active.is_(True),
    )).all()
    for plan in plans:
        if plan.workspace_id in own_workspaces:
            continue
        workspace = db.get(Workspace, plan.workspace_id)
        current_month = datetime.now(ZoneInfo(workspace.timezone)).date().replace(day=1)
        plan.active = False
        db.execute(delete(IncomeOccurrence).where(
            IncomeOccurrence.plan_id == plan.id,
            IncomeOccurrence.month > current_month,
        ))

    db.execute(update(Invite).where(
        Invite.created_by == target.id,
        Invite.used_at.is_(None),
        Invite.revoked_at.is_(None),
    ).values(revoked_at=datetime.now(timezone.utc)))
    for workspace_id in own_workspaces:
        db.delete(db.get(Workspace, workspace_id))
    db.flush()
    db.delete(target)
    db.commit()
    response.headers["Cache-Control"] = "no-store"
