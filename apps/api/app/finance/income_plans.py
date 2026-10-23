"""Rendas previstas por pessoa e recebimentos que entram no caixa uma só vez."""

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

from app.finance.cycles import day_in_month
from app.finance.models import Movement
from app.finance.recurrence_models import IncomeOccurrence, IncomePlan, IncomeReceipt
from app.finance.routes import (
    MAX_CENTS,
    account_or_404,
    require_after_opening,
    require_current_month,
    today,
)
from app.identity.dependencies import CurrentUser, Db
from app.identity.models import Membership
from app.identity.workspaces import require_member

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["income-plans"])


class PlanInput(BaseModel):
    description: str = Field(min_length=1, max_length=120)
    amount_cents: int = Field(gt=0, le=MAX_CENTS)
    day_of_month: int = Field(ge=1, le=31)
    responsible_user_id: UUID

    @field_validator("description")
    @classmethod
    def clean_description(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("Informe a descrição da renda.")
        return value


class AdjustInput(BaseModel):
    expected_cents: int = Field(gt=0, le=MAX_CENTS)


class ReceiveInput(BaseModel):
    account_id: UUID
    amount_cents: int = Field(gt=0, le=MAX_CENTS)
    occurred_on: date
    complete: bool
    request_id: str = Field(min_length=8, max_length=80)


def require_responsible(db, workspace_id, user_id):
    if db.get(Membership, (workspace_id, user_id)) is None:
        raise HTTPException(422, "Escolha uma pessoa que participa deste espaço.")


def serialize_plan(row):
    return {
        "id": row.id,
        "description": row.description,
        "amount_cents": row.amount_cents,
        "day_of_month": row.day_of_month,
        "responsible_user_id": row.responsible_user_id,
        "start_month": row.start_month,
        "active": row.active,
    }


def received_total(db, occurrence_id):
    return (
        db.scalar(
            select(func.sum(Movement.amount_cents))
            .join(IncomeReceipt, IncomeReceipt.movement_id == Movement.id)
            .where(IncomeReceipt.occurrence_id == occurrence_id)
        )
        or 0
    )


def serialize_occurrence(db, row, plan):
    received = received_total(db, row.id)
    return {
        "id": row.id,
        "plan_id": plan.id,
        "month": row.month,
        "due_on": row.due_on,
        "description": row.description,
        "responsible_user_id": row.responsible_user_id,
        "expected_cents": row.expected_cents,
        "received_cents": received,
        "remaining_cents": 0 if row.completed else max(0, row.expected_cents - received),
        "completed": row.completed,
        "reminded_on": row.reminded_on,
    }


def generate_month(db, workspace_id, month):
    plans = db.scalars(
        select(IncomePlan).where(
            IncomePlan.workspace_id == workspace_id,
            IncomePlan.active.is_(True),
            IncomePlan.start_month <= month,
        )
    ).all()
    existing = set(db.scalars(
        select(IncomeOccurrence.plan_id).join(IncomePlan, IncomePlan.id == IncomeOccurrence.plan_id)
        .where(IncomePlan.workspace_id == workspace_id, IncomeOccurrence.month == month)
    ))
    for plan in plans:
        if plan.id in existing:
            continue
        db.add(
            IncomeOccurrence(
                plan_id=plan.id,
                month=month,
                due_on=day_in_month(month, plan.day_of_month),
                expected_cents=plan.amount_cents,
                description=plan.description,
                responsible_user_id=plan.responsible_user_id,
                completed=False,
            )
        )
    db.flush()


def plan_or_404(db, workspace_id, plan_id):
    row = db.get(IncomePlan, plan_id)
    if row is None or row.workspace_id != workspace_id:
        raise HTTPException(404, "Previsão de renda não encontrada.")
    return row


def occurrence_or_404(db, workspace_id, occurrence_id):
    row = db.get(IncomeOccurrence, occurrence_id)
    plan = db.get(IncomePlan, row.plan_id) if row else None
    if plan is None or plan.workspace_id != workspace_id:
        raise HTTPException(404, "Recebimento previsto não encontrado.")
    return row, plan


@router.get("/income-plans")
def list_plans(workspace_id: UUID, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id)
    return [
        serialize_plan(row)
        for row in db.scalars(
            select(IncomePlan)
            .where(IncomePlan.workspace_id == workspace_id)
            .order_by(IncomePlan.description)
        ).all()
    ]


@router.post("/income-plans", status_code=201)
def create_plan(workspace_id: UUID, data: PlanInput, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    require_responsible(db, workspace_id, data.responsible_user_id)
    current = today(workspace)
    row = IncomePlan(
        workspace_id=workspace_id,
        start_month=current.replace(day=1),
        active=True,
        created_at=datetime.now(timezone.utc),
        **data.model_dump(),
    )
    db.add(row)
    db.flush()
    generate_month(db, workspace_id, current.replace(day=1))
    db.commit()
    return serialize_plan(row)


@router.patch("/income-plans/{plan_id}")
def edit_plan(workspace_id: UUID, plan_id: UUID, data: PlanInput, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    row = plan_or_404(db, workspace_id, plan_id)
    if not row.active:
        raise HTTPException(409, "Esta previsão está desativada.")
    require_responsible(db, workspace_id, data.responsible_user_id)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    current_month = today(workspace).replace(day=1)
    for occurrence in db.scalars(
        select(IncomeOccurrence).where(
            IncomeOccurrence.plan_id == row.id,
            IncomeOccurrence.month >= current_month,
            IncomeOccurrence.completed.is_(False),
        )
    ).all():
        occurrence.due_on = day_in_month(occurrence.month, row.day_of_month)
        occurrence.expected_cents = row.amount_cents
        occurrence.description = row.description
        occurrence.responsible_user_id = row.responsible_user_id
    db.commit()
    return serialize_plan(row)


@router.delete("/income-plans/{plan_id}", status_code=204)
def deactivate_plan(workspace_id: UUID, plan_id: UUID, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    row = plan_or_404(db, workspace_id, plan_id)
    row.active = False
    future = db.scalars(select(IncomeOccurrence).where(
        IncomeOccurrence.plan_id == row.id,
        IncomeOccurrence.month > today(workspace).replace(day=1),
    )).all()
    for occurrence in future:
        db.delete(occurrence)
    db.commit()


@router.get("/income-occurrences")
def list_occurrences(
    workspace_id: UUID,
    db: Db,
    user: CurrentUser,
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    year, number = map(int, month.split("-"))
    target = date(year, number, 1)
    if target >= today(workspace).replace(day=1):
        generate_month(db, workspace_id, target)
    db.commit()
    rows = db.execute(
        select(IncomeOccurrence, IncomePlan)
        .join(IncomePlan, IncomeOccurrence.plan_id == IncomePlan.id)
        .where(IncomePlan.workspace_id == workspace_id, IncomeOccurrence.month == target)
        .order_by(IncomeOccurrence.due_on, IncomeOccurrence.id)
    ).all()
    return [serialize_occurrence(db, row, plan) for row, plan in rows]


@router.patch("/income-occurrences/{occurrence_id}")
def adjust_occurrence(
    workspace_id: UUID, occurrence_id: UUID, data: AdjustInput, db: Db, user: CurrentUser
):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    row, plan = occurrence_or_404(db, workspace_id, occurrence_id)
    require_current_month(workspace, row.due_on)
    if row.completed:
        raise HTTPException(409, "Este recebimento já foi concluído.")
    row.expected_cents = data.expected_cents
    db.commit()
    return serialize_occurrence(db, row, plan)


@router.get("/income-reminders")
def due_reminders(workspace_id: UUID, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    current = today(workspace)
    generate_month(db, workspace_id, current.replace(day=1))
    db.commit()
    rows = db.execute(
        select(IncomeOccurrence, IncomePlan)
        .join(IncomePlan, IncomeOccurrence.plan_id == IncomePlan.id)
        .where(
            IncomePlan.workspace_id == workspace_id,
            IncomeOccurrence.month == current.replace(day=1),
            IncomeOccurrence.due_on <= current,
            IncomeOccurrence.completed.is_(False),
            (IncomeOccurrence.reminded_on.is_(None) | (IncomeOccurrence.reminded_on < current)),
        )
        .order_by(IncomeOccurrence.due_on)
    ).all()
    return [
        item
        for row, plan in rows
        if (item := serialize_occurrence(db, row, plan))["remaining_cents"] > 0
    ]


@router.post("/income-occurrences/{occurrence_id}/defer")
def defer_reminder(workspace_id: UUID, occurrence_id: UUID, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    row, plan = occurrence_or_404(db, workspace_id, occurrence_id)
    require_current_month(workspace, row.due_on)
    row.reminded_on = today(workspace)
    db.commit()
    return serialize_occurrence(db, row, plan)


@router.post("/income-occurrences/{occurrence_id}/receive")
def receive(workspace_id: UUID, occurrence_id: UUID, data: ReceiveInput, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    row, plan = occurrence_or_404(db, workspace_id, occurrence_id)
    duplicate = db.scalar(
        select(IncomeReceipt).where(
            IncomeReceipt.occurrence_id == row.id, IncomeReceipt.request_id == data.request_id
        )
    )
    if duplicate:
        return serialize_occurrence(db, row, plan)
    require_current_month(workspace, data.occurred_on)
    if row.month != data.occurred_on.replace(day=1):
        raise HTTPException(422, "Receba esta renda no mês da previsão.")
    account = account_or_404(db, workspace_id, data.account_id)
    require_after_opening(account, data.occurred_on)
    remaining = max(0, row.expected_cents - received_total(db, row.id))
    if row.completed:
        raise HTTPException(409, "Esta previsão já foi concluída.")
    movement = Movement(
        workspace_id=workspace_id,
        account_id=account.id,
        kind="income",
        amount_cents=data.amount_cents,
        occurred_on=data.occurred_on,
        note=row.description,
        created_at=datetime.now(timezone.utc),
    )
    db.add(movement)
    db.flush()
    db.add(IncomeReceipt(occurrence_id=row.id, movement_id=movement.id, request_id=data.request_id))
    row.completed = data.complete or data.amount_cents >= remaining
    row.reminded_on = today(workspace)
    db.commit()
    return serialize_occurrence(db, row, plan)
