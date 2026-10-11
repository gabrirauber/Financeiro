from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.identity.auth import NameInput
from app.identity.dependencies import CurrentUser, Db
from app.identity.models import Membership, User, Workspace

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def require_member(db, workspace_id, user_id, *, admin=False, lock=False):
    # Todas as mutações da participação usam a mesma ordem de locks.
    workspace = (
        db.scalar(select(Workspace).where(Workspace.id == workspace_id).with_for_update())
        if lock
        else db.get(Workspace, workspace_id)
    )
    membership = db.get(Membership, (workspace_id, user_id))
    if workspace is None or membership is None:
        raise HTTPException(404, "Espaço não encontrado.")
    if admin and membership.role != "admin":
        raise HTTPException(403, "Somente o administrador pode fazer isso.")
    return workspace, membership


@router.post("", status_code=201)
def create(data: NameInput, db: Db, user: CurrentUser):
    from app.finance.categories import seed_categories

    db.scalar(select(User).where(User.id == user.id).with_for_update())
    if db.scalar(select(Membership).where(Membership.user_id == user.id)):
        raise HTTPException(409, "Você já participa de um espaço financeiro.")
    workspace = Workspace(name=data.name)
    db.add(workspace)
    db.flush()
    db.add(Membership(workspace_id=workspace.id, user_id=user.id, role="admin"))
    seed_categories(db, workspace.id)
    db.commit()
    return {"id": workspace.id, "name": workspace.name, "role": "admin"}


@router.get("")
def list_spaces(db: Db, user: CurrentUser):
    rows = db.execute(
        select(Workspace, Membership.role)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == user.id)
        .order_by(Workspace.name)
    ).all()
    return [{"id": workspace.id, "name": workspace.name, "role": role} for workspace, role in rows]


@router.get("/{workspace_id}/members")
def members(workspace_id: UUID, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id)
    rows = db.execute(
        select(User.id, User.email, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.workspace_id == workspace_id)
        .order_by(User.email)
    ).all()
    return [{"id": id_, "email": email, "role": role} for id_, email, role in rows]


@router.delete("/{workspace_id}/members/{user_id}", status_code=204)
def remove_member(workspace_id: UUID, user_id: UUID, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id, admin=True, lock=True)
    target = db.get(Membership, (workspace_id, user_id))
    if target is None:
        raise HTTPException(404, "Participante não encontrado.")
    if target.role == "admin":
        raise HTTPException(409, "Não é possível remover o administrador.")
    db.delete(target)
    db.commit()
