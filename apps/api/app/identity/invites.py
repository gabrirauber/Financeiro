import secrets
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.identity.dependencies import CurrentUser, Db
from app.identity.models import Invite, Membership, User, Workspace
from app.identity.security import digest, now, throttle
from app.identity.workspaces import require_member

router = APIRouter(tags=["invites"])


class CodeInput(BaseModel):
    code: str = Field(min_length=1, max_length=64)


@router.post("/workspaces/{workspace_id}/invites", status_code=201)
def create_invite(workspace_id: UUID, db: Db, user: CurrentUser):
    throttle(db, "invite-create:", str(user.id), 30)
    require_member(db, workspace_id, user.id, admin=True, lock=True)
    code = secrets.token_hex(6).upper()
    invite = Invite(
        workspace_id=workspace_id,
        created_by=user.id,
        token_hash=digest(code),
        expires_at=now() + timedelta(hours=24),
    )
    db.add(invite)
    db.commit()
    return {"id": invite.id, "code": code, "expires_at": invite.expires_at}


@router.get("/workspaces/{workspace_id}/invites")
def list_invites(workspace_id: UUID, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id, admin=True)
    rows = db.scalars(
        select(Invite).where(
            Invite.workspace_id == workspace_id,
            Invite.used_at.is_(None),
            Invite.revoked_at.is_(None),
            Invite.expires_at > now(),
        )
    ).all()
    return [{"id": item.id, "expires_at": item.expires_at} for item in rows]


@router.delete("/workspaces/{workspace_id}/invites/{invite_id}", status_code=204)
def revoke(workspace_id: UUID, invite_id: UUID, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id, admin=True, lock=True)
    invite = db.get(Invite, invite_id)
    if invite is None or invite.workspace_id != workspace_id:
        raise HTTPException(404, "Convite não encontrado.")
    invite.revoked_at = now()
    db.commit()


@router.post("/invites/accept")
def accept(data: CodeInput, db: Db, user: CurrentUser):
    throttle(db, "invite-accept:", str(user.id), 15)
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    workspace = claim_invite(db, user, data.code)
    db.commit()
    return {"id": workspace.id, "name": workspace.name, "role": "member"}


def claim_invite(db, user, code):
    if db.scalar(select(Membership).where(Membership.user_id == user.id)):
        raise HTTPException(409, "Você já participa de um espaço financeiro.")
    token_hash = digest(code.strip().upper())
    candidate = db.scalar(select(Invite).where(Invite.token_hash == token_hash))
    if candidate is None:
        raise HTTPException(400, "Código inválido, expirado ou já utilizado.")
    # Serializar aceite, revogação e alterações de membros no mesmo espaço.
    workspace = db.scalar(
        select(Workspace).where(Workspace.id == candidate.workspace_id).with_for_update()
    )
    invite = db.scalar(
        select(Invite)
        .where(Invite.id == candidate.id)
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    if (
        not workspace
        or not invite
        or invite.used_at
        or invite.revoked_at
        or invite.expires_at <= now()
    ):
        raise HTTPException(400, "Código inválido, expirado ou já utilizado.")
    invite.used_at = now()
    db.add(Membership(workspace_id=workspace.id, user_id=user.id, role="member"))
    return workspace


@router.post("/workspaces/{workspace_id}/transfer-admin/{user_id}", status_code=204)
def transfer_admin(workspace_id: UUID, user_id: UUID, db: Db, user: CurrentUser):
    _, actor = require_member(db, workspace_id, user.id, admin=True, lock=True)
    target = db.get(Membership, (workspace_id, user_id))
    if target is None or user_id == user.id:
        raise HTTPException(400, "Selecione outro participante do espaço.")
    actor.role = "member"
    target.role = "admin"
    db.commit()


@router.post("/workspaces/{workspace_id}/leave", status_code=204)
def leave(workspace_id: UUID, db: Db, user: CurrentUser):
    _, actor = require_member(db, workspace_id, user.id, lock=True)
    if actor.role == "admin":
        raise HTTPException(409, "Transfira a administração antes de sair.")
    db.delete(actor)
    db.commit()
