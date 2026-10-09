from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import case, func, select

from app.finance.models import Account, Movement
from app.identity.dependencies import CurrentUser, Db
from app.identity.workspaces import require_member

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["finance"])
MAX_CENTS = 999_999_999


class AccountInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: Literal["bank", "cash"]
    opening_balance_cents: int = Field(ge=0, le=MAX_CENTS)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("Informe a descrição da conta.")
        return value


class IncomeInput(BaseModel):
    account_id: UUID
    amount_cents: int = Field(gt=0, le=MAX_CENTS)
    occurred_on: date
    note: str = Field(default="", max_length=200)


class TransferInput(BaseModel):
    from_account_id: UUID
    to_account_id: UUID
    amount_cents: int = Field(gt=0, le=MAX_CENTS)
    occurred_on: date
    note: str = Field(default="", max_length=200)


def today(workspace):
    return datetime.now(ZoneInfo(workspace.timezone)).date()


def require_current_month(workspace, day):
    current = today(workspace)
    if (day.year, day.month) != (current.year, current.month):
        raise HTTPException(422, "Somente movimentações do mês corrente são permitidas.")


def account_or_404(db, workspace_id, account_id):
    account = db.get(Account, account_id)
    if account is None or account.workspace_id != workspace_id:
        raise HTTPException(404, "Conta não encontrada.")
    return account


def require_after_opening(account, day):
    if day < account.opened_on:
        raise HTTPException(422, "A data não pode ser anterior ao cadastro da conta.")


def account_balances(db, workspace_id):
    # Saldos derivados do mesmo extrato que o usuário consulta; nunca há dois saldos a sincronizar.
    signed = case(
        (Movement.kind.in_(("transfer_out", "expense")), -Movement.amount_cents),
        else_=Movement.amount_cents,
    )
    totals = dict(
        db.execute(
            select(Movement.account_id, func.sum(signed))
            .where(Movement.workspace_id == workspace_id)
            .group_by(Movement.account_id)
        ).all()
    )
    return [
        {
            "id": account.id,
            "name": account.name,
            "kind": account.kind,
            "opening_balance_cents": account.opening_balance_cents,
            "opened_on": account.opened_on,
            "balance_cents": account.opening_balance_cents + (totals.get(account.id) or 0),
        }
        for account in db.scalars(
            select(Account)
            .where(Account.workspace_id == workspace_id)
            .order_by(Account.name, Account.id)
        )
    ]


@router.get("/accounts")
def list_accounts(workspace_id: UUID, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id)
    return account_balances(db, workspace_id)


@router.post("/accounts", status_code=201)
def create_account(workspace_id: UUID, data: AccountInput, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    current = today(workspace)
    account = Account(
        workspace_id=workspace_id,
        name=data.name,
        kind=data.kind,
        opening_balance_cents=data.opening_balance_cents,
        opened_on=current,
    )
    db.add(account)
    db.commit()
    return {
        "id": account.id,
        "name": account.name,
        "kind": account.kind,
        "opening_balance_cents": account.opening_balance_cents,
        "opened_on": account.opened_on,
        "balance_cents": account.opening_balance_cents,
    }


@router.get("/accounts/{account_id}/statement")
def statement(workspace_id: UUID, account_id: UUID, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id)
    account = account_or_404(db, workspace_id, account_id)
    rows = db.scalars(
        select(Movement)
        .where(Movement.workspace_id == workspace_id, Movement.account_id == account.id)
        .order_by(Movement.occurred_on.desc(), Movement.created_at.desc(), Movement.id.desc())
    ).all()
    return [
        {
            "id": row.id,
            "kind": row.kind,
            "amount_cents": row.amount_cents,
            "occurred_on": row.occurred_on,
            "note": row.note,
            "transfer_id": row.transfer_id,
        }
        for row in rows
    ]


@router.post("/incomes", status_code=201)
def create_income(workspace_id: UUID, data: IncomeInput, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    require_current_month(workspace, data.occurred_on)
    account = account_or_404(db, workspace_id, data.account_id)
    require_after_opening(account, data.occurred_on)
    row = Movement(
        workspace_id=workspace_id,
        account_id=data.account_id,
        kind="income",
        amount_cents=data.amount_cents,
        occurred_on=data.occurred_on,
        note=data.note.strip(),
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    return {
        "id": row.id,
        "account_id": row.account_id,
        "amount_cents": row.amount_cents,
        "occurred_on": row.occurred_on,
        "note": row.note,
    }


@router.patch("/incomes/{income_id}")
def edit_income(workspace_id: UUID, income_id: UUID, data: IncomeInput, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    row = db.get(Movement, income_id)
    if row is None or row.workspace_id != workspace_id or row.kind != "income":
        raise HTTPException(404, "Receita não encontrada.")
    require_current_month(workspace, row.occurred_on)
    require_current_month(workspace, data.occurred_on)
    account = account_or_404(db, workspace_id, data.account_id)
    require_after_opening(account, data.occurred_on)
    row.account_id = data.account_id
    row.amount_cents = data.amount_cents
    row.occurred_on = data.occurred_on
    row.note = data.note.strip()
    db.commit()
    return {
        "id": row.id,
        "account_id": row.account_id,
        "amount_cents": row.amount_cents,
        "occurred_on": row.occurred_on,
        "note": row.note,
    }


@router.delete("/incomes/{income_id}", status_code=204)
def delete_income(workspace_id: UUID, income_id: UUID, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    row = db.get(Movement, income_id)
    if row is None or row.workspace_id != workspace_id or row.kind != "income":
        raise HTTPException(404, "Receita não encontrada.")
    require_current_month(workspace, row.occurred_on)
    db.delete(row)
    db.commit()


@router.post("/transfers", status_code=201)
def create_transfer(workspace_id: UUID, data: TransferInput, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    require_current_month(workspace, data.occurred_on)
    if data.from_account_id == data.to_account_id:
        raise HTTPException(422, "Escolha duas contas diferentes.")
    origin = account_or_404(db, workspace_id, data.from_account_id)
    target = account_or_404(db, workspace_id, data.to_account_id)
    require_after_opening(origin, data.occurred_on)
    require_after_opening(target, data.occurred_on)
    transfer_id = uuid4()
    created_at = datetime.now(timezone.utc)
    note = data.note.strip()
    db.add_all(
        [
            Movement(
                workspace_id=workspace_id,
                account_id=data.from_account_id,
                kind="transfer_out",
                amount_cents=data.amount_cents,
                occurred_on=data.occurred_on,
                note=note,
                transfer_id=transfer_id,
                created_at=created_at,
            ),
            Movement(
                workspace_id=workspace_id,
                account_id=data.to_account_id,
                kind="transfer_in",
                amount_cents=data.amount_cents,
                occurred_on=data.occurred_on,
                note=note,
                transfer_id=transfer_id,
                created_at=created_at,
            ),
        ]
    )
    db.commit()
    return {
        "id": transfer_id,
        "from_account_id": data.from_account_id,
        "to_account_id": data.to_account_id,
        "amount_cents": data.amount_cents,
        "occurred_on": data.occurred_on,
        "note": note,
    }


@router.delete("/transfers/{transfer_id}", status_code=204)
def delete_transfer(workspace_id: UUID, transfer_id: UUID, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    rows = db.scalars(
        select(Movement).where(
            Movement.workspace_id == workspace_id, Movement.transfer_id == transfer_id
        )
    ).all()
    if len(rows) != 2:
        raise HTTPException(404, "Transferência não encontrada.")
    require_current_month(workspace, rows[0].occurred_on)
    for row in rows:
        db.delete(row)
    db.commit()


@router.patch("/transfers/{transfer_id}")
def edit_transfer(
    workspace_id: UUID, transfer_id: UUID, data: TransferInput, db: Db, user: CurrentUser
):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    rows = db.scalars(
        select(Movement).where(
            Movement.workspace_id == workspace_id, Movement.transfer_id == transfer_id
        )
    ).all()
    if len(rows) != 2:
        raise HTTPException(404, "Transferência não encontrada.")
    require_current_month(workspace, rows[0].occurred_on)
    require_current_month(workspace, data.occurred_on)
    if data.from_account_id == data.to_account_id:
        raise HTTPException(422, "Escolha duas contas diferentes.")
    origin = account_or_404(db, workspace_id, data.from_account_id)
    target = account_or_404(db, workspace_id, data.to_account_id)
    require_after_opening(origin, data.occurred_on)
    require_after_opening(target, data.occurred_on)
    for row in rows:
        row.account_id = data.from_account_id if row.kind == "transfer_out" else data.to_account_id
        row.amount_cents = data.amount_cents
        row.occurred_on = data.occurred_on
        row.note = data.note.strip()
    db.commit()
    return {
        "id": transfer_id,
        "from_account_id": data.from_account_id,
        "to_account_id": data.to_account_id,
        "amount_cents": data.amount_cents,
        "occurred_on": data.occurred_on,
        "note": data.note.strip(),
    }


@router.get("/transfers/{transfer_id}")
def get_transfer(workspace_id: UUID, transfer_id: UUID, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id)
    rows = db.scalars(
        select(Movement).where(
            Movement.workspace_id == workspace_id, Movement.transfer_id == transfer_id
        )
    ).all()
    if len(rows) != 2:
        raise HTTPException(404, "Transferência não encontrada.")
    outgoing = next(row for row in rows if row.kind == "transfer_out")
    incoming = next(row for row in rows if row.kind == "transfer_in")
    return {
        "id": transfer_id,
        "from_account_id": outgoing.account_id,
        "to_account_id": incoming.account_id,
        "amount_cents": outgoing.amount_cents,
        "occurred_on": outgoing.occurred_on,
        "note": outgoing.note,
    }
