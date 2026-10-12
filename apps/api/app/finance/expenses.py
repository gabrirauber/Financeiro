from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.finance.categories import category_or_404, subcategory_or_404
from app.finance.models import Expense, Movement
from app.finance.routes import (
    MAX_CENTS,
    account_or_404,
    require_after_opening,
    require_current_month,
)
from app.identity.dependencies import CurrentUser, Db
from app.identity.workspaces import require_member

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["expenses"])


class ExpenseInput(BaseModel):
    account_id: UUID
    category_id: UUID
    subcategory_id: UUID
    amount_cents: int = Field(gt=0, le=MAX_CENTS)
    occurred_on: date
    payment_method: Literal["pix", "debit", "cash"]
    note: str = Field(default="", max_length=200)


def validate_expense(db, workspace_id, data, existing=None):
    account = account_or_404(db, workspace_id, data.account_id)
    require_after_opening(account, data.occurred_on)
    if data.payment_method == "cash" and account.kind != "cash":
        raise HTTPException(422, "Pagamento em dinheiro exige uma conta do tipo dinheiro.")
    if data.payment_method != "cash" and account.kind != "bank":
        raise HTTPException(422, "Pix ou débito exigem uma conta bancária.")
    category = category_or_404(db, workspace_id, data.category_id)
    sub = subcategory_or_404(db, category.id, data.subcategory_id)
    unchanged = existing and (existing.category_id, existing.subcategory_id) == (
        data.category_id,
        data.subcategory_id,
    )
    if not unchanged and (not category.active or not sub.active):
        raise HTTPException(422, "Escolha uma categoria e subcategoria ativas.")


def serialize(expense, movement):
    return {
        "id": expense.id,
        "account_id": movement.account_id,
        "category_id": expense.category_id,
        "subcategory_id": expense.subcategory_id,
        "amount_cents": movement.amount_cents,
        "occurred_on": movement.occurred_on,
        "payment_method": expense.payment_method,
        "note": movement.note,
    }


def expense_or_404(db, workspace_id, expense_id):
    expense = db.get(Expense, expense_id)
    if expense is None or expense.workspace_id != workspace_id:
        raise HTTPException(404, "Despesa não encontrada.")
    return expense


@router.get("/expenses")
def list_expenses(
    workspace_id: UUID,
    db: Db,
    user: CurrentUser,
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
):
    require_member(db, workspace_id, user.id)
    year, number = map(int, month.split("-"))
    if year < 1 or (year == 9999 and number == 12):
        raise HTTPException(422, "Mês inválido.")
    start = date(year, number, 1)
    end = date(year + (number == 12), number % 12 + 1, 1)
    rows = db.execute(
        select(Expense, Movement)
        .join(Movement, Movement.id == Expense.movement_id)
        .where(
            Expense.workspace_id == workspace_id,
            Movement.occurred_on >= start,
            Movement.occurred_on < end,
        )
        .order_by(Movement.occurred_on.desc(), Movement.created_at.desc(), Expense.id.desc())
    ).all()
    return [serialize(expense, movement) for expense, movement in rows]


@router.post("/expenses", status_code=201)
def create_expense(workspace_id: UUID, data: ExpenseInput, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    require_current_month(workspace, data.occurred_on)
    validate_expense(db, workspace_id, data)
    from datetime import datetime, timezone

    movement = Movement(
        workspace_id=workspace_id,
        account_id=data.account_id,
        kind="expense",
        amount_cents=data.amount_cents,
        occurred_on=data.occurred_on,
        note=data.note.strip(),
        created_at=datetime.now(timezone.utc),
    )
    db.add(movement)
    db.flush()
    expense = Expense(
        workspace_id=workspace_id,
        movement_id=movement.id,
        category_id=data.category_id,
        subcategory_id=data.subcategory_id,
        payment_method=data.payment_method,
    )
    db.add(expense)
    db.commit()
    return serialize(expense, movement)


@router.patch("/expenses/{expense_id}")
def edit_expense(
    workspace_id: UUID, expense_id: UUID, data: ExpenseInput, db: Db, user: CurrentUser
):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    expense = expense_or_404(db, workspace_id, expense_id)
    movement = db.get(Movement, expense.movement_id)
    require_current_month(workspace, movement.occurred_on)
    require_current_month(workspace, data.occurred_on)
    validate_expense(db, workspace_id, data, expense)
    movement.account_id = data.account_id
    movement.amount_cents = data.amount_cents
    movement.occurred_on = data.occurred_on
    movement.note = data.note.strip()
    expense.category_id = data.category_id
    expense.subcategory_id = data.subcategory_id
    expense.payment_method = data.payment_method
    db.commit()
    return serialize(expense, movement)


@router.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(workspace_id: UUID, expense_id: UUID, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    expense = expense_or_404(db, workspace_id, expense_id)
    movement = db.get(Movement, expense.movement_id)
    require_current_month(workspace, movement.occurred_on)
    from app.finance.recurrence_models import RecurringOccurrence

    occurrence = db.scalar(
        select(RecurringOccurrence).where(RecurringOccurrence.expense_id == expense.id)
    )
    if occurrence:
        occurrence.expense_id = None
        db.flush()
    db.delete(expense)
    db.delete(movement)
    db.commit()
