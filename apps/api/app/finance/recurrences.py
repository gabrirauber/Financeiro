"""Geração mensal idempotente de contas fixas e assinaturas no cartão."""

from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from app.finance.card_models import CardInstallment, CardPurchase, Invoice
from app.finance.cards import card_or_404, ensure_invoice, invoice_settled
from app.finance.categories import category_or_404, subcategory_or_404
from app.finance.cycles import cycle_for_due_month, day_in_month, first_cycle, shift_month
from app.finance.expenses import ExpenseInput, validate_expense
from app.finance.models import Expense, Movement
from app.finance.recurrence_models import RecurringOccurrence, RecurringRule
from app.finance.routes import MAX_CENTS, require_current_month, today
from app.identity.dependencies import CurrentUser, Db
from app.identity.workspaces import require_member

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["recurrences"])


class RuleInput(BaseModel):
    kind: Literal["expense", "card"]
    description: str = Field(min_length=1, max_length=120)
    amount_cents: int = Field(gt=0, le=MAX_CENTS)
    day_of_month: int = Field(ge=1, le=31)
    category_id: UUID
    subcategory_id: UUID
    payment_method: Literal["pix", "debit", "cash"] | None = None
    card_id: UUID | None = None

    @field_validator("description")
    @classmethod
    def clean_description(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("Informe a descrição da recorrência.")
        return value


class PayFixedInput(BaseModel):
    account_id: UUID
    amount_cents: int = Field(gt=0, le=MAX_CENTS)
    occurred_on: date
    payment_method: Literal["pix", "debit", "cash"]


def validate_rule(db, workspace_id, data):
    category = category_or_404(db, workspace_id, data.category_id)
    sub = subcategory_or_404(db, category.id, data.subcategory_id)
    if not category.active or not sub.active:
        raise HTTPException(422, "Escolha uma categoria e subcategoria ativas.")
    if data.kind == "card":
        if data.card_id is None or data.payment_method is not None:
            raise HTTPException(422, "Escolha um cartão para esta recorrência.")
        if not card_or_404(db, workspace_id, data.card_id).active:
            raise HTTPException(422, "Escolha um cartão ativo.")
    elif data.card_id is not None or data.payment_method is None:
        raise HTTPException(422, "Escolha a forma de pagamento da despesa fixa.")


def serialize_rule(row):
    return {
        "id": row.id,
        "kind": row.kind,
        "description": row.description,
        "amount_cents": row.amount_cents,
        "day_of_month": row.day_of_month,
        "start_month": row.start_month,
        "category_id": row.category_id,
        "subcategory_id": row.subcategory_id,
        "payment_method": row.payment_method,
        "card_id": row.card_id,
        "active": row.active,
    }


def serialize_occurrence(db, row, rule):
    movement = None
    if row.expense_id:
        expense = db.get(Expense, row.expense_id)
        movement = db.get(Movement, expense.movement_id) if expense else None
    return {
        "id": row.id,
        "rule_id": rule.id,
        "kind": rule.kind,
        "description": row.description,
        "month": row.month,
        "due_on": row.due_on,
        "amount_cents": row.amount_cents,
        "category_id": row.category_id,
        "subcategory_id": row.subcategory_id,
        "payment_method": row.payment_method,
        "card_id": row.card_id,
        "expense_id": row.expense_id,
        "purchase_id": row.purchase_id,
        "paid_cents": movement.amount_cents if movement else None,
        "paid_on": movement.occurred_on if movement else None,
    }


def generate_month(db, workspace_id, month, current):
    if month < current.replace(day=1):
        return
    rules = db.scalars(
        select(RecurringRule).where(
            RecurringRule.workspace_id == workspace_id,
            RecurringRule.active.is_(True),
            RecurringRule.start_month <= month,
        )
    ).all()
    for rule in rules:
        occurrence = db.scalar(
            select(RecurringOccurrence).where(
                RecurringOccurrence.rule_id == rule.id, RecurringOccurrence.month == month
            )
        )
        if occurrence is None:
            occurrence = RecurringOccurrence(
                rule_id=rule.id,
                month=month,
                due_on=day_in_month(month, rule.day_of_month),
                amount_cents=rule.amount_cents,
                description=rule.description,
                category_id=rule.category_id,
                subcategory_id=rule.subcategory_id,
                payment_method=rule.payment_method,
                card_id=rule.card_id,
            )
            db.add(occurrence)
            db.flush()
        if rule.kind != "card" or occurrence.due_on > current or occurrence.purchase_id:
            continue
        card = card_or_404(db, workspace_id, occurrence.card_id)
        if not card.active:
            continue
        invoice_month = first_cycle(card, occurrence.due_on)[0]
        for _ in range(13):
            existing = db.scalar(
                select(Invoice).where(Invoice.card_id == card.id, Invoice.month == invoice_month)
            )
            closes_on = (
                existing.closes_on if existing else cycle_for_due_month(card, invoice_month)[1]
            )
            if closes_on >= current and (
                existing is None or not invoice_settled(db, existing, current)
            ):
                break
            invoice_month = shift_month(invoice_month, 1)
        invoice = ensure_invoice(db, card, invoice_month, current)
        purchase = CardPurchase(
            card_id=card.id,
            purchased_on=occurrence.due_on,
            total_cents=occurrence.amount_cents,
            legacy=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(purchase)
        db.flush()
        db.add(
            CardInstallment(
                purchase_id=purchase.id,
                invoice_id=invoice.id,
                sequence=1,
                total_count=1,
                amount_cents=occurrence.amount_cents,
                category_id=occurrence.category_id,
                subcategory_id=occurrence.subcategory_id,
                note=occurrence.description,
            )
        )
        occurrence.purchase_id = purchase.id


def rule_or_404(db, workspace_id, rule_id):
    row = db.get(RecurringRule, rule_id)
    if row is None or row.workspace_id != workspace_id:
        raise HTTPException(404, "Recorrência não encontrada.")
    return row


@router.get("/recurring-rules")
def list_rules(workspace_id: UUID, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id)
    return [
        serialize_rule(row)
        for row in db.scalars(
            select(RecurringRule)
            .where(RecurringRule.workspace_id == workspace_id)
            .order_by(RecurringRule.description)
        ).all()
    ]


@router.post("/recurring-rules", status_code=201)
def create_rule(workspace_id: UUID, data: RuleInput, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    validate_rule(db, workspace_id, data)
    current = today(workspace)
    row = RecurringRule(
        workspace_id=workspace_id,
        start_month=current.replace(day=1),
        active=True,
        created_at=datetime.now(timezone.utc),
        **data.model_dump(),
    )
    db.add(row)
    db.flush()
    generate_month(db, workspace_id, current.replace(day=1), current)
    db.commit()
    return serialize_rule(row)


@router.patch("/recurring-rules/{rule_id}")
def edit_rule(workspace_id: UUID, rule_id: UUID, data: RuleInput, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    row = rule_or_404(db, workspace_id, rule_id)
    if not row.active or row.kind != data.kind:
        raise HTTPException(409, "Não é possível mudar o tipo da recorrência.")
    validate_rule(db, workspace_id, data)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    current_month = today(workspace).replace(day=1)
    pending = db.scalars(
        select(RecurringOccurrence).where(
            RecurringOccurrence.rule_id == row.id,
            RecurringOccurrence.month >= current_month,
            RecurringOccurrence.expense_id.is_(None),
            RecurringOccurrence.purchase_id.is_(None),
        )
    ).all()
    for occurrence in pending:
        occurrence.due_on = day_in_month(occurrence.month, row.day_of_month)
        occurrence.amount_cents = row.amount_cents
        occurrence.description = row.description
        occurrence.category_id = row.category_id
        occurrence.subcategory_id = row.subcategory_id
        occurrence.payment_method = row.payment_method
        occurrence.card_id = row.card_id
    db.commit()
    return serialize_rule(row)


@router.delete("/recurring-rules/{rule_id}", status_code=204)
def deactivate_rule(workspace_id: UUID, rule_id: UUID, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    row = rule_or_404(db, workspace_id, rule_id)
    row.active = False
    future = db.scalars(select(RecurringOccurrence).where(
        RecurringOccurrence.rule_id == row.id,
        RecurringOccurrence.month > today(workspace).replace(day=1),
        RecurringOccurrence.expense_id.is_(None),
        RecurringOccurrence.purchase_id.is_(None),
    )).all()
    for occurrence in future:
        db.delete(occurrence)
    db.commit()


@router.get("/recurring-occurrences")
def list_occurrences(
    workspace_id: UUID,
    db: Db,
    user: CurrentUser,
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    year, number = map(int, month.split("-"))
    target = date(year, number, 1)
    current = today(workspace)
    generate_month(db, workspace_id, target, current)
    db.commit()
    rows = db.execute(
        select(RecurringOccurrence, RecurringRule)
        .join(RecurringRule, RecurringOccurrence.rule_id == RecurringRule.id)
        .where(RecurringRule.workspace_id == workspace_id, RecurringOccurrence.month == target)
        .order_by(RecurringOccurrence.due_on, RecurringOccurrence.id)
    ).all()
    return [serialize_occurrence(db, row, rule) for row, rule in rows]


@router.post("/recurring-occurrences/{occurrence_id}/pay")
def pay_fixed(
    workspace_id: UUID, occurrence_id: UUID, data: PayFixedInput, db: Db, user: CurrentUser
):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    row = db.get(RecurringOccurrence, occurrence_id)
    rule = db.get(RecurringRule, row.rule_id) if row else None
    if rule is None or rule.workspace_id != workspace_id or rule.kind != "expense":
        raise HTTPException(404, "Despesa fixa não encontrada.")
    if row.expense_id:
        return serialize_occurrence(db, row, rule)
    require_current_month(workspace, data.occurred_on)
    if row.month != data.occurred_on.replace(day=1):
        raise HTTPException(422, "Pague esta despesa no mês da previsão.")
    expense_input = ExpenseInput(
        account_id=data.account_id,
        category_id=row.category_id,
        subcategory_id=row.subcategory_id,
        amount_cents=data.amount_cents,
        occurred_on=data.occurred_on,
        payment_method=data.payment_method,
        note=row.description,
    )
    validate_expense(db, workspace_id, expense_input, row)
    movement = Movement(
        workspace_id=workspace_id,
        account_id=data.account_id,
        kind="expense",
        amount_cents=data.amount_cents,
        occurred_on=data.occurred_on,
        note=row.description,
        created_at=datetime.now(timezone.utc),
    )
    db.add(movement)
    db.flush()
    expense = Expense(
        workspace_id=workspace_id,
        movement_id=movement.id,
        category_id=row.category_id,
        subcategory_id=row.subcategory_id,
        payment_method=data.payment_method,
    )
    db.add(expense)
    db.flush()
    row.expense_id = expense.id
    db.commit()
    return serialize_occurrence(db, row, rule)
